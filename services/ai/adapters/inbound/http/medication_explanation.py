"""HTTP adapter for contracts/api/ai/medication-warning-explanation.v1.yaml (HC-156).

The body is parsed here, strictly. The explanation runs in the threadpool, because
provider adapters may start their own event loop (the Claude adapter calls asyncio.run).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from application.explain_medication_warning import (
    ExplainMedicationWarning,
    ExplanationResult,
)
from domain.medication_explanation import (
    InvalidWarning,
    MedicationWarning,
    RuleSource,
    SafetySourceKind,
    Severity,
)

PATH = "/v1/medication-warning-explanations"
CONTRACT_VERSION = "1.0"
NOTICE = (
    "Advisory explanation of a medication warning. The warning comes from a "
    "deterministic rule set or a validated source, never from AI; this text only puts "
    "it in words and does not change its severity. The clinician decides."
)

OpaqueRef = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]
Text = Annotated[str, Field(min_length=1, max_length=500)]


class MedicationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=200)]
    # Accepted for compatibility with the medication contract; not used.
    code: dict | None = None


class RuleSourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SafetySourceKind
    name: Text
    version: Text
    rule_id: Text
    reference: Annotated[str, Field(max_length=500)] | None = None


class WarningBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warning_id: Text
    type: Literal["drug_drug_interaction"]
    severity: Severity
    summary: Text
    proposed_medication: MedicationBody
    conflicting_medication: MedicationBody
    rule_source: RuleSourceBody


class ExplanationRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_by: OpaqueRef
    warning: WarningBody


def _problem(detail: str) -> JSONResponse:
    return JSONResponse(
        {
            "type": "about:blank",
            "title": "Invalid medication warning explanation request",
            "status": 400,
            "detail": detail,
            "code": "invalid_request",
        },
        status_code=400,
        media_type="application/problem+json",
    )


def _wire(result: ExplanationResult) -> dict:
    explanation = result.explanation
    by = explanation.generated_by
    return {
        "explanation_id": result.explanation_id,
        "contract_version": CONTRACT_VERSION,
        "warning_id": result.warning_id,
        "advisory": True,
        "review_status": "pending_clinician_review",
        "notice": NOTICE,
        # Exactly medication-safety-check.v1.yaml's Explanation, ready for Warning.explanation.
        "explanation": {
            "text": explanation.text,
            "advisory": True,
            "generated_by": {
                "kind": by.kind.value,
                "name": by.name,
                "version": by.version,
                "mocked": by.mocked,
            },
            "generated_at": explanation.generated_at.isoformat(),
        },
        "rejected_reasons": list(result.rejected_reasons),
        "uncertainty_notes": list(result.uncertainty_notes),
    }


def create_router(explain: ExplainMedicationWarning) -> APIRouter:
    router = APIRouter()

    @router.post(PATH)
    async def create_medication_warning_explanation(request: Request) -> JSONResponse:
        try:
            body = ExplanationRequestBody.model_validate_json(await request.body())
            w = body.warning
            warning = MedicationWarning(
                warning_id=w.warning_id,
                severity=w.severity,
                summary=w.summary,
                proposed_medication=w.proposed_medication.name,
                conflicting_medication=w.conflicting_medication.name,
                rule_source=RuleSource(
                    w.rule_source.kind,
                    w.rule_source.name,
                    w.rule_source.version,
                    w.rule_source.rule_id,
                    w.rule_source.reference,
                ),
            )
        except ValidationError as error:
            fields = sorted(
                {".".join(str(p) for p in e["loc"]) or "body" for e in error.errors()}
            )
            return _problem("Invalid or missing fields: " + ", ".join(fields))
        except InvalidWarning as error:
            return _problem(str(error))
        result = await run_in_threadpool(explain, warning)
        return JSONResponse(_wire(result))

    return router
