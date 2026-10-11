"""contracts/api/medication-safety/medication-safety-check.v1.yaml (HC-162).

Requests are parsed strictly; anything outside the contract is a 400 invalid_request.
When no check is performed the answer is a 503 safety_check_unavailable, never an empty
list of warnings. Callers are not authenticated (demo depth), and nothing in the
request is stored.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from application.check_medication_safety import (
    CheckMedicationSafety,
    CheckNotPerformed,
    SafetyCheckRequest,
    SafetyCheckResult,
)
from domain.medication_safety import (
    Coding,
    Medication,
    MedicationStatement,
    StatementSource,
    StatementStatus,
)

PATH = "/v1/medication-safety-checks"
CONTRACT_VERSION = "1.0"
WARNINGS_NOTICE = (
    "Potential interaction for clinician review. The prescribing decision belongs to "
    "the clinician."
)
NO_WARNINGS_NOTICE = (
    "No interaction found among the medications the rule source could evaluate. This "
    "is not a statement that the prescription is safe."
)
MOCKED_NOTICE = " Fictional demo rules (MOCKED), not a validated source."

OpaqueRef = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]


class CodingBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system: Annotated[str, Field(min_length=1)]
    code: Annotated[str, Field(min_length=1)]
    display: str | None = None


class MedicationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=200)]
    # Required, and null when the source gives no code.
    code: CodingBody | None


class SourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_ref: OpaqueRef
    recorded_at: AwareDatetime | None = None


class StatementBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement_ref: OpaqueRef
    medication: MedicationBody
    status: Literal["active", "stopped", "unknown"]
    source: SourceBody


class CheckBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_ref: OpaqueRef
    encounter_ref: OpaqueRef | None = None
    requested_by: OpaqueRef
    proposed_medication: MedicationBody
    current_medications: Annotated[list[StatementBody], Field(max_length=200)]


def _medication(body: MedicationBody) -> Medication:
    code = body.code
    return Medication(
        body.name, Coding(code.system, code.code, code.display) if code else None
    )


def _request(body: CheckBody) -> SafetyCheckRequest:
    return SafetyCheckRequest(
        patient_ref=body.patient_ref,
        encounter_ref=body.encounter_ref,
        requested_by=body.requested_by,
        proposed_medication=_medication(body.proposed_medication),
        current_medications=tuple(
            MedicationStatement(
                statement_ref=s.statement_ref,
                medication=_medication(s.medication),
                status=StatementStatus(s.status),
                source=StatementSource(
                    s.source.organization_ref,
                    s.source.recorded_at.isoformat() if s.source.recorded_at else None,
                ),
            )
            for s in body.current_medications
        ),
    )


def _problem(status: int, title: str, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        {
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
        },
        status_code=status,
        media_type="application/problem+json",
    )


def _medication_wire(medication: Medication) -> dict:
    code = None
    if medication.code is not None:
        code = {"system": medication.code.system, "code": medication.code.code}
        if medication.code.display is not None:
            code["display"] = medication.code.display
    return {"name": medication.name, "code": code}


def _source_wire(source: StatementSource) -> dict:
    wire = {"organization_ref": source.organization_ref}
    if source.recorded_at is not None:
        wire["recorded_at"] = source.recorded_at
    return wire


def _wire(result: SafetyCheckResult) -> dict:
    request, outcome, rules = result.request, result.outcome, result.rule_set
    notice = WARNINGS_NOTICE if outcome.warnings_found else NO_WARNINGS_NOTICE
    body = {
        "check_id": result.check_id,
        "contract_version": CONTRACT_VERSION,
        "patient_ref": request.patient_ref,
        "requested_by": request.requested_by,
        "outcome": "warnings_found" if outcome.warnings_found else "no_warnings_found",
        "review_status": "pending_clinician_review",
        "notice": notice + (MOCKED_NOTICE if result.mocked else ""),
        "warnings": [
            {
                "warning_id": f"warning-{index}",
                "type": "drug_drug_interaction",
                "severity": w.rule.severity.value,
                "summary": w.rule.summary,
                "proposed_medication": _medication_wire(w.proposed_medication),
                "conflicting_statement_ref": w.conflicting.statement_ref,
                "conflicting_medication": _medication_wire(w.conflicting.medication),
                "conflicting_source": _source_wire(w.conflicting.source),
                "rule_source": {
                    "kind": rules.kind.value,
                    "name": rules.name,
                    "version": rules.version,
                    "rule_id": w.rule.rule_id,
                    "reference": w.rule.reference,
                },
                # The optional AI explanation is attached by HC-164, not here.
                "explanation": None,
            }
            for index, w in enumerate(outcome.warnings, start=1)
        ],
        "unevaluated_medications": [
            {
                "statement_ref": u.statement.statement_ref,
                "medication": _medication_wire(u.statement.medication),
                "reason": u.reason.value,
            }
            for u in outcome.unevaluated
        ],
        "provenance": {
            "engine": {
                "kind": result.engine.kind.value,
                "name": result.engine.name,
                "version": result.engine.version,
            },
            "mocked": result.mocked,
            "evaluated_at": result.evaluated_at.isoformat(),
        },
    }
    if request.encounter_ref is not None:
        body["encounter_ref"] = request.encounter_ref
    return body


def create_router(check: CheckMedicationSafety) -> APIRouter:
    router = APIRouter(tags=["medication safety"])

    @router.post(PATH)
    async def create_medication_safety_check(request: Request) -> JSONResponse:
        try:
            body = CheckBody.model_validate_json(await request.body())
        except ValidationError as error:
            fields = sorted(
                {".".join(str(p) for p in e["loc"]) or "body" for e in error.errors()}
            )
            return _problem(
                400,
                "Invalid medication safety check request",
                "invalid_request",
                "Invalid or missing fields: " + ", ".join(fields),
            )
        try:
            result = check(_request(body))
        except CheckNotPerformed as error:
            return _problem(
                503,
                "Medication safety check unavailable",
                "safety_check_unavailable",
                str(error),
            )
        return JSONResponse(_wire(result))

    return router
