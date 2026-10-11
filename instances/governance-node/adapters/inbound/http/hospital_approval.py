"""contracts/api/governance/hospital-approval.v1.yaml (HC-131).

Lists and reads hospital applications, records a reviewer's decision, and reads an
approval decision. Requests are parsed strictly; anything outside the contract is a
400 invalid_request. With authentication required (HC-211), every operation needs a
bearer session whose role grants governance review (HC-212), and a decision's
reviewer_ref must be the signed-in person; off, reviewer_ref is declared.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

from adapters.inbound.http.authentication import AccessControl
from adapters.inbound.http.problems import OPAQUE_REF, first_error, problem

from application.audit import AuditTrail
from application.hospital_approval import (
    ApplicationNotFound,
    HospitalApplicationStore,
    ReviewerDirectory,
    decide_application,
    get_application,
    get_hospital_approval,
    list_applications,
)
from application.ledger import AuditLedgerPort
from domain.access_control import Permission
from domain.policy import PolicyHistory
from domain.hospital_application import ApplicationStatus, HospitalApplication
from domain.hospital_approval import (
    DecisionDraft,
    HospitalApprovalDecision,
    InvalidDecision,
    NotAwaitingReview,
    Outcome,
    ReviewerNotAllowed,
)

NOTICE = (
    "Fictional demo applications, held in memory by the Governance Node: decisions "
    "are lost on restart, and requests are not authenticated."
)


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer_ref: Annotated[str, Field(pattern=OPAQUE_REF.pattern)]
    outcome: Literal["approved", "rejected"]
    rationale: Annotated[str, Field(max_length=2000)]
    conditions: Annotated[
        list[Annotated[str, Field(max_length=500)]], Field(max_length=10)
    ]
    findings_acknowledged: StrictBool


def _invalid(detail: str) -> JSONResponse:
    return problem(400, "Invalid request", "invalid_request", detail)


def _application_not_found(application_ref: str) -> JSONResponse:
    return problem(
        404,
        "Application not found",
        "application_not_found",
        f"No hospital application {application_ref}.",
    )


def _summary(application: HospitalApplication) -> dict:
    return {
        "application_ref": application.application_ref,
        "organization_ref": application.organization_ref,
        "status": application.status.value,
        "submitted_at": application.submitted_at.isoformat(),
        "decision_ref": application.decision_ref,
        "findings_count": application.findings.count,
    }


def _decision(decision: HospitalApprovalDecision) -> dict:
    return {
        "decision_ref": decision.decision_ref,
        "application_ref": decision.application_ref,
        "organization_ref": decision.organization_ref,
        "outcome": decision.outcome.value,
        "decided_by_ref": decision.decided_by_ref,
        "decided_at": decision.decided_at.isoformat(),
        "policy_ref": decision.policy_ref,
        "rationale": decision.rationale,
        "conditions": list(decision.conditions),
    }


def _detail(
    application: HospitalApplication, decision: HospitalApprovalDecision | None
) -> dict:
    findings = application.findings
    return {
        **_summary(application),
        "findings": {
            "missing_documents": [
                {"document_ref": d.document_ref, "type": d.type, "title": d.title}
                for d in findings.missing_documents
            ],
            "unaccepted_agreements": list(findings.unaccepted_agreements),
            "completeness_findings": list(findings.completeness_findings),
            "advisory_findings": list(findings.advisory_findings),
        },
        "decision": _decision(decision) if decision else None,
    }


def create_router(
    store: HospitalApplicationStore,
    reviewers: ReviewerDirectory,
    policies: PolicyHistory,
    audit: AuditTrail,
    clock: Callable[[], datetime],
    ledger: AuditLedgerPort,
    auth: AccessControl,
) -> APIRouter:
    router = APIRouter(tags=["hospital approval"])

    @router.get("/v1/hospital-applications")
    def list_hospital_applications(
        request: Request, status: str | None = None
    ) -> JSONResponse:
        if isinstance(caller := auth.caller(request, Permission.REVIEW), JSONResponse):
            return caller
        try:
            wanted = ApplicationStatus(status) if status is not None else None
        except ValueError:
            allowed = ", ".join(s.value for s in ApplicationStatus)
            return _invalid(f"status must be one of: {allowed}")
        return JSONResponse(
            {
                "notice": NOTICE,
                "applications": [_summary(a) for a in list_applications(store, wanted)],
            }
        )

    @router.get("/v1/hospital-applications/{application_ref}")
    def get_hospital_application(
        application_ref: str, request: Request
    ) -> JSONResponse:
        if isinstance(caller := auth.caller(request, Permission.REVIEW), JSONResponse):
            return caller
        try:
            application, decision = get_application(application_ref, store)
        except ApplicationNotFound:
            return _application_not_found(application_ref)
        return JSONResponse(_detail(application, decision))

    @router.post("/v1/hospital-applications/{application_ref}/decision")
    async def decide_hospital_application(
        application_ref: str, request: Request
    ) -> JSONResponse:
        caller = auth.caller(request, Permission.REVIEW)
        if isinstance(caller, JSONResponse):
            return caller
        if store.application(application_ref) is None:
            return _application_not_found(application_ref)
        try:
            body = DecisionRequest.model_validate_json(await request.body())
        except ValidationError as error:
            return _invalid(first_error(error))
        if (refused := auth.refuse(caller, body.reviewer_ref)) is not None:
            return refused
        draft = DecisionDraft(
            outcome=Outcome(body.outcome),
            rationale=body.rationale,
            conditions=tuple(body.conditions),
            findings_acknowledged=body.findings_acknowledged,
        )
        try:
            decision = decide_application(
                application_ref,
                body.reviewer_ref,
                draft,
                store,
                reviewers,
                policies,
                audit,
                clock,
                ledger,
            )
        except ApplicationNotFound:
            return _application_not_found(application_ref)
        except NotAwaitingReview as error:
            return problem(
                409, "Not awaiting review", "not_awaiting_review", str(error)
            )
        except ReviewerNotAllowed as error:
            return problem(
                403, "Reviewer not allowed", "reviewer_not_allowed", str(error)
            )
        except InvalidDecision as error:
            return problem(
                422,
                "Invalid decision",
                "invalid_decision",
                f"The decision breaks {len(error.issues)} review rule(s).",
                issues=[{"field": i.field, "message": i.message} for i in error.issues],
            )
        return JSONResponse(_decision(decision), status_code=201)

    @router.get("/v1/hospital-approvals/{decision_ref}")
    def get_approval(decision_ref: str, request: Request) -> JSONResponse:
        if isinstance(caller := auth.caller(request, Permission.REVIEW), JSONResponse):
            return caller
        decision = get_hospital_approval(decision_ref, store)
        if decision is None:
            return problem(
                404,
                "Decision not found",
                "decision_not_found",
                f"No hospital approval decision {decision_ref}.",
            )
        return JSONResponse(_decision(decision))

    return router
