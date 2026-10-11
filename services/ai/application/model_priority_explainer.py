"""Priority queue explanation through any AiProvider (HC-157).

The model is given the entry as the priority method ranked it, without any patient
reference or factor id (factors are F1, F2, ... by position), and asked to put it in
plain words for a clinician. It is not asked whether the ranking is right or how
urgent the patient is: the method has decided the ranking, and nobody here assesses
urgency. ExplainPriorityEntry checks its text before use.
"""

import json
from collections.abc import Callable
from uuid import uuid4

from application.ai_provider import AiProvider, AiProviderError, AiRequest, AiTask
from application.explanation import (
    OUTPUT_SCHEMA,
    ExplanationUnavailable,
    ProposedExplanation,
    explanation_text,
)
from domain.explanation import GeneratedBy, GeneratorKind
from domain.priority_explanation import MAX_EXPLANATION_LENGTH, QueueEntry, citation

INSTRUCTIONS = f"""\
You explain to a clinician why a patient sits where they do in their priority queue.
A deterministic priority method ranked the entry from the factors given; the ranking
is correct as given. You only explain it.

Return JSON matching this schema:
{json.dumps(OUTPUT_SCHEMA)}

Rules:
- Two to four sentences, at most {MAX_EXPLANATION_LENGTH} characters, in the language of
  the factor labels.
- State the priority with the words "priorité haute", "priorité moyenne" or "priorité
  basse" (in English: "high priority", "medium priority", "low priority"). Do not name
  any other priority, and do not soften or strengthen it.
- Explain every factor, and cite each one right after you mention it with its ref in
  brackets, for example [F1]. Cite only the refs given.
- Use only the entry's content. Do not add a number, a value, a factor, a diagnosis, or
  an interpretation of the patient's condition that the entry does not state.
- Call the patient "le patient" (in English "the patient"): the entry does not give
  their sex.
- Do not mention urgency at all, not even to deny it, and do not tell the clinician
  what to do or whom to see first. Say that the ranking is not a clinical triage, and
  end by saying the decision belongs to the clinician.
"""


class ModelPriorityExplainer:
    def __init__(
        self,
        provider: AiProvider,
        new_request_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._provider = provider
        self._new_request_id = new_request_id

    def explain(self, entry: QueueEntry) -> ProposedExplanation:
        try:
            output = self._provider.generate(
                AiRequest(
                    request_id=self._new_request_id(),
                    task=AiTask.EXPLANATION,
                    instructions=INSTRUCTIONS,
                    input_text=_entry_json(entry),
                    output_schema=OUTPUT_SCHEMA,
                )
            )
        except AiProviderError as error:
            raise ExplanationUnavailable(str(error)) from error
        provenance = output.provenance
        return ProposedExplanation(
            text=explanation_text(output.text),
            generated_by=GeneratedBy(
                kind=GeneratorKind.MODEL,
                name=provenance.provider_id,
                version=provenance.model_id,
                mocked=provenance.is_mock,
            ),
            uncertainty_notes=output.uncertainty_notes,
        )


def _entry_json(entry: QueueEntry) -> str:
    method = entry.method
    return json.dumps(
        {
            "rank": entry.rank,
            "priority": entry.priority.value,
            "score": entry.score,
            "factors": [
                {
                    "ref": citation(i),
                    "type": f.type.value,
                    "label": f.label,
                    "severity": f.severity.value,
                    "weight": f.weight,
                }
                for i, f in enumerate(entry.factors)
            ],
            "method": {
                "kind": method.kind.value,
                "name": method.name,
                "version": method.version,
                "description": method.description,
            },
        },
        ensure_ascii=False,
    )
