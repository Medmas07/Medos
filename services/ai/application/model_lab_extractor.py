"""Lab result extraction through any AiProvider (HC-155).

The model only reads the report: test, value, unit, the printed reference range, and a
verbatim quote. It is not asked whether a value is abnormal; ExtractLabResults verifies
every row and computes the flag from the printed range.
"""

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from application.ai_provider import AiProvider, AiProviderError, AiRequest, AiTask
from application.extract_lab_results import (
    LabExtractionUnavailable,
    LabExtractorOutput,
)
from domain.lab_extraction import (
    ExtractorInfo,
    ExtractorKind,
    InvalidLabExtraction,
    ProposedResult,
    ReferenceRange,
)

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["results"],
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "test",
                    "value",
                    "unit",
                    "reference_low",
                    "reference_high",
                    "quote",
                ],
                "properties": {
                    "test": {"type": "string"},
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                    "reference_low": {"type": ["number", "null"]},
                    "reference_high": {"type": ["number", "null"]},
                    "quote": {"type": "string"},
                },
            },
        },
    },
}

INSTRUCTIONS = f"""\
You read a laboratory report and copy its numeric results into JSON for a clinician to
check. You do not interpret results, judge whether a value is normal or abnormal,
diagnose, or add anything the report does not print.

Return JSON matching this schema:
{json.dumps(OUTPUT_SCHEMA)}

Rules:
- One entry per numeric result printed in the report. Skip results that are not a
  number (for example "négatif" or "absent").
- test: the test name as printed. unit: the unit as printed.
- value: the number as printed, as a JSON number (a decimal comma becomes a point).
- reference_low and reference_high: the reference range printed with that result, as
  numbers; null when the report prints none for it. Never use a usual or typical range.
- quote: the exact, contiguous text of the report's line for that result, including
  the value and its printed range, copied character for character.
- If there is no numeric result, return an empty list.
"""


class ModelLabExtractor:
    def __init__(
        self,
        provider: AiProvider,
        new_request_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._provider = provider
        self._new_request_id = new_request_id

    def extract(self, report: str) -> LabExtractorOutput:
        try:
            output = self._provider.generate(
                AiRequest(
                    request_id=self._new_request_id(),
                    task=AiTask.EXTRACTION,
                    instructions=INSTRUCTIONS,
                    input_text=report,
                    output_schema=OUTPUT_SCHEMA,
                )
            )
        except AiProviderError as error:
            raise LabExtractionUnavailable(str(error)) from error
        proposals, malformed = _proposals(_parse(output.text))
        provenance = output.provenance
        return LabExtractorOutput(
            proposals=proposals,
            malformed=malformed,
            extractor=ExtractorInfo(
                kind=ExtractorKind.MODEL,
                name=provenance.provider_id,
                version=provenance.model_id,
                mocked=provenance.is_mock,
            ),
            uncertainty_notes=output.uncertainty_notes,
        )


def _parse(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise LabExtractionUnavailable(
            "The model did not return valid JSON."
        ) from error
    if not isinstance(payload, dict):
        raise LabExtractionUnavailable("The model did not return a JSON object.")
    return payload


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _proposals(payload: dict[str, Any]) -> tuple[tuple[ProposedResult, ...], int]:
    """Well-formed rows, which the use case verifies, and how many were not."""
    proposals, malformed = [], 0
    raw = payload.get("results")
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            malformed += 1
            continue
        test, unit, quote = entry.get("test"), entry.get("unit"), entry.get("quote")
        value = _number(entry.get("value"))
        if not all(isinstance(x, str) for x in (test, unit, quote)) or value is None:
            malformed += 1
            continue
        low, high = (
            _number(entry.get("reference_low")),
            _number(entry.get("reference_high")),
        )
        try:
            reference_range = (
                ReferenceRange(low, high)
                if low is not None and high is not None
                else None
            )
        except InvalidLabExtraction:
            reference_range = None
        proposals.append(ProposedResult(test, value, unit, quote, reference_range))
    return tuple(proposals), malformed
