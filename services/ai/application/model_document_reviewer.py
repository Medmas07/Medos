"""Hospital dossier review through any AiProvider (HC-154).

The model only proposes findings; ReviewHospitalDocuments keeps those whose citations
exist in the dossier. The instructions keep the model to completeness, consistency, and
clarification: it never judges whether the hospital should join.
"""

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from application.ai_provider import AiProvider, AiProviderError, AiRequest, AiTask
from application.review_hospital_documents import ReviewerOutput, ReviewUnavailable
from domain.document_review import (
    DocumentQuote,
    Dossier,
    FindingCategory,
    ReviewerInfo,
    ReviewerKind,
    ReviewFinding,
)

CATEGORIES = [category.value for category in FindingCategory]

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["category", "message", "field_paths", "evidence"],
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "message": {"type": "string"},
                    "field_paths": {"type": "array", "items": {"type": "string"}},
                    "evidence": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                        "required": ["document_ref", "quote"],
                        "properties": {
                            "document_ref": {"type": "string"},
                            "quote": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}

INSTRUCTIONS = f"""\
You assist a human governance reviewer who checks a hospital's application to join a
federated healthcare network. You review the application dossier for completeness and
consistency only. You do not decide, recommend approval or rejection, score the
application, or judge the hospital's quality. A human reviewer decides.

The dossier is JSON: `fields` (path and value) and `documents` (metadata and, sometimes,
extracted text). Return JSON matching this schema:
{json.dumps(OUTPUT_SCHEMA)}

Rules:
- category: `inconsistency` when two answers or an answer and a document contradict each
  other; `missing_information` when an answer a reviewer would expect is empty or null;
  `clarification_needed` when an answer is present but leaves a practical question for
  the onboarding (for example deployment or DMI integration).
- message: one or two sentences for the reviewer, in the language of the dossier.
- field_paths: the exact `path` values of the fields the finding is about, copied from
  the dossier. Never invent a path.
- evidence: when a document's text supports the finding, its `document_ref` and an exact,
  contiguous quote copied character for character; otherwise null.
- Do not report a missing document by its status alone: the completeness check already
  does. Do not repeat the same point twice.
- If you find nothing, return an empty list.
"""


class ModelDocumentReviewer:
    def __init__(
        self,
        provider: AiProvider,
        new_request_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._provider = provider
        self._new_request_id = new_request_id

    def review(self, dossier: Dossier) -> ReviewerOutput:
        try:
            output = self._provider.generate(
                AiRequest(
                    request_id=self._new_request_id(),
                    task=AiTask.REVIEW,
                    instructions=INSTRUCTIONS,
                    input_text=_dossier_json(dossier),
                    output_schema=OUTPUT_SCHEMA,
                )
            )
        except AiProviderError as error:
            raise ReviewUnavailable(str(error)) from error
        provenance = output.provenance
        findings, uncited = _findings(_parse(output.text))
        return ReviewerOutput(
            findings=findings,
            uncited=uncited,
            reviewer=ReviewerInfo(
                kind=ReviewerKind.MODEL,
                name=provenance.provider_id,
                version=provenance.model_id,
                mocked=provenance.is_mock,
            ),
            uncertainty_notes=output.uncertainty_notes,
        )


def _dossier_json(dossier: Dossier) -> str:
    return json.dumps(
        {
            "fields": [{"path": f.path, "value": f.value} for f in dossier.fields],
            "documents": [
                {
                    "document_ref": d.document_ref,
                    "type": d.type,
                    "title": d.title,
                    "status": d.status,
                    "text": d.text,
                }
                for d in dossier.documents
            ],
        },
        ensure_ascii=False,
    )


def _parse(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ReviewUnavailable("The model did not return valid JSON.") from error
    if not isinstance(payload, dict):
        raise ReviewUnavailable("The model did not return a JSON object.")
    return payload


def _findings(payload: dict[str, Any]) -> tuple[tuple[ReviewFinding, ...], int]:
    """Well-formed proposals, whose citations the use case checks, and how many cited
    nothing at all."""
    findings, uncited = [], 0
    raw = payload.get("findings")
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict) or entry.get("category") not in CATEGORIES:
            continue
        message = entry.get("message")
        if not (isinstance(message, str) and message.strip()):
            continue
        paths = entry.get("field_paths")
        paths = (
            tuple(p for p in paths if isinstance(p, str))
            if isinstance(paths, list)
            else ()
        )
        evidence = None
        raw_evidence = entry.get("evidence")
        if isinstance(raw_evidence, dict):
            ref, quote = raw_evidence.get("document_ref"), raw_evidence.get("quote")
            if isinstance(ref, str) and isinstance(quote, str) and quote.strip():
                evidence = DocumentQuote(ref, quote)
        if not paths and evidence is None:
            uncited += 1
            continue
        findings.append(
            ReviewFinding(
                finding_id=f"proposal-{len(findings) + 1}",
                category=FindingCategory(entry["category"]),
                message=message.strip(),
                field_paths=paths,
                evidence=evidence,
            )
        )
    return tuple(findings), uncited
