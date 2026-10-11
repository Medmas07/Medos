"""Medication warning explanation through any AiProvider (HC-156).

The model is given the warning's content only and asked to put it in plain words for a
clinician. It is not asked whether the interaction is real or how serious it is: the
rule source has decided both. ExplainMedicationWarning checks its text before use.
"""

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from application.ai_provider import AiProvider, AiProviderError, AiRequest, AiTask
from application.explain_medication_warning import (
    ExplanationUnavailable,
    ProposedExplanation,
)
from domain.medication_explanation import (
    MAX_EXPLANATION_LENGTH,
    GeneratedBy,
    GeneratorKind,
    MedicationWarning,
)

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["explanation"],
    "properties": {"explanation": {"type": "string"}},
}

INSTRUCTIONS = f"""\
You explain a medication interaction warning to a clinician in plain language. The
warning was produced by a deterministic rule set or a validated source; it is correct
as given. You only explain it.

Return JSON matching this schema:
{json.dumps(OUTPUT_SCHEMA)}

Rules:
- Two to four sentences, at most {MAX_EXPLANATION_LENGTH} characters, in the language of
  the warning's summary.
- Name both medications exactly as given.
- Use only the warning's content. Do not add other interactions, mechanisms, or
  medications that the warning does not state.
- State the warning's severity in words (for example "majeure" or "major" for major).
  Do not name any other severity, and do not soften or strengthen it.
- Never give a dose, a quantity, a frequency, or a prescription; do not tell the
  clinician what to prescribe. End by saying the decision belongs to the clinician.
"""


class ModelWarningExplainer:
    def __init__(
        self,
        provider: AiProvider,
        new_request_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._provider = provider
        self._new_request_id = new_request_id

    def explain(self, warning: MedicationWarning) -> ProposedExplanation:
        try:
            output = self._provider.generate(
                AiRequest(
                    request_id=self._new_request_id(),
                    task=AiTask.EXPLANATION,
                    instructions=INSTRUCTIONS,
                    input_text=_warning_json(warning),
                    output_schema=OUTPUT_SCHEMA,
                )
            )
        except AiProviderError as error:
            raise ExplanationUnavailable(str(error)) from error
        text = _text(output.text)
        provenance = output.provenance
        return ProposedExplanation(
            text=text,
            generated_by=GeneratedBy(
                kind=GeneratorKind.MODEL,
                name=provenance.provider_id,
                version=provenance.model_id,
                mocked=provenance.is_mock,
            ),
            uncertainty_notes=output.uncertainty_notes,
        )


def _warning_json(warning: MedicationWarning) -> str:
    source = warning.rule_source
    return json.dumps(
        {
            "severity": warning.severity.value,
            "summary": warning.summary,
            "proposed_medication": warning.proposed_medication,
            "conflicting_medication": warning.conflicting_medication,
            "rule_source": {
                "kind": source.kind.value,
                "name": source.name,
                "version": source.version,
                "rule_id": source.rule_id,
            },
        },
        ensure_ascii=False,
    )


def _text(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ExplanationUnavailable("The model did not return valid JSON.") from error
    text = payload.get("explanation") if isinstance(payload, dict) else None
    if not isinstance(text, str):
        raise ExplanationUnavailable("The model returned no explanation text.")
    return text
