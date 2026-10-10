"""Clinical extraction through any AiProvider (HC-153).

The model only proposes items. Each item must quote its evidence verbatim from
the source text; items whose quote cannot be found are dropped, so the draft
never shows a claim the clinician cannot check against the source.
"""

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from application.ai_provider import AiProvider, AiProviderError, AiRequest, AiTask
from application.extract_clinical_information import (
    ExtractionUnavailable,
    ExtractorOutput,
)
from domain.clinical_extraction import (
    Evidence,
    ExtractedItem,
    ExtractionSource,
    ExtractorInfo,
    ExtractorKind,
    ItemCategory,
    MissingInformation,
)

CATEGORIES = [category.value for category in ItemCategory]

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items", "missing_information"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "category",
                    "text",
                    "evidence_quote",
                    "value",
                    "unit",
                    "abnormal",
                ],
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "text": {"type": "string"},
                    "evidence_quote": {"type": "string"},
                    "value": {"type": ["number", "null"]},
                    "unit": {"type": ["string", "null"]},
                    "abnormal": {"type": ["boolean", "null"]},
                },
            },
        },
        "missing_information": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["topic", "prompt"],
                "properties": {
                    "topic": {"type": "string"},
                    "prompt": {"type": "string"},
                },
            },
        },
    },
}

INSTRUCTIONS = f"""\
You extract structured information from clinical text for a clinician to review.
You do not diagnose, recommend treatment, or add facts that the text does not state.

Return JSON matching this schema:
{json.dumps(OUTPUT_SCHEMA)}

Rules:
- One item per distinct fact. category is one of: {", ".join(CATEGORIES)}.
- diagnosis_mentioned only for a diagnosis the text explicitly names.
- text: a short statement of the fact, in the language of the source.
- evidence_quote: an exact, contiguous substring of the source text that supports the item. Copy it character for character.
- value and unit: only for measurements, as written in the source (split combined values such as blood pressure into separate items). Otherwise null.
- abnormal: true or false only when a measurement is clearly outside the usual adult reference range; otherwise null. It is a suggestion for review, not a finding.
- missing_information: information a clinician would usually record for this kind of text that is not mentioned (for example allergies, medication dose). Use a short snake_case topic and a one-sentence prompt.
- If nothing can be extracted, return empty lists.
"""


class ModelClinicalExtractor:
    def __init__(
        self,
        provider: AiProvider,
        new_request_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._provider = provider
        self._new_request_id = new_request_id

    def extract(self, source: ExtractionSource) -> ExtractorOutput:
        try:
            output = self._provider.generate(
                AiRequest(
                    request_id=self._new_request_id(),
                    task=AiTask.EXTRACTION,
                    instructions=INSTRUCTIONS,
                    input_text=source.text,
                    output_schema=OUTPUT_SCHEMA,
                )
            )
        except AiProviderError as error:
            raise ExtractionUnavailable(str(error)) from error

        payload = _parse(output.text)
        provenance = output.provenance
        return ExtractorOutput(
            items=_items(payload.get("items"), source.text),
            missing_information=_missing(payload.get("missing_information")),
            info=ExtractorInfo(
                kind=ExtractorKind.MODEL,
                name=provenance.provider_id,
                version=provenance.model_id,
                mocked=provenance.is_mock,
            ),
        )


def _parse(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ExtractionUnavailable("The model did not return valid JSON.") from error
    if not isinstance(payload, dict):
        raise ExtractionUnavailable("The model did not return a JSON object.")
    return payload


def _locate(quote: str, text: str) -> Evidence | None:
    start = text.find(quote)
    if start < 0:
        # Accept a case-only difference, but keep the source's own characters as the quote.
        start = text.lower().find(quote.lower())
    if start < 0:
        return None
    end = start + len(quote)
    return Evidence(quote=text[start:end], start=start, end=end)


def _items(raw: Any, text: str) -> tuple[ExtractedItem, ...]:
    items: list[ExtractedItem] = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict) or entry.get("category") not in CATEGORIES:
            continue
        statement, quote = entry.get("text"), entry.get("evidence_quote")
        if not (isinstance(statement, str) and statement.strip()):
            continue
        if not (isinstance(quote, str) and quote.strip()):
            continue
        evidence = _locate(quote.strip(), text)
        if evidence is None:
            continue
        value = entry.get("value")
        unit = entry.get("unit")
        abnormal = entry.get("abnormal")
        items.append(
            ExtractedItem(
                item_id=f"item-{len(items) + 1}",
                category=ItemCategory(entry["category"]),
                text=statement.strip(),
                evidence=evidence,
                value=value
                if isinstance(value, int | float) and not isinstance(value, bool)
                else None,
                unit=unit if isinstance(unit, str) and unit.strip() else None,
                abnormal=abnormal if isinstance(abnormal, bool) else None,
                # Self-reported model confidence is not calibrated, so none is reported.
                confidence=None,
            )
        )
    return tuple(items)


def _missing(raw: Any) -> tuple[MissingInformation, ...]:
    entries = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        topic, prompt = entry.get("topic"), entry.get("prompt")
        if (
            isinstance(topic, str)
            and topic.strip()
            and isinstance(prompt, str)
            and prompt.strip()
        ):
            entries.append(
                MissingInformation(topic=topic.strip(), prompt=prompt.strip())
            )
    return tuple(entries)
