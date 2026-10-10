"""contracts/api/governance/synchronization-requests.v1.yaml (HC-132).

Submits, lists, and reads synchronization requests, and records a reviewer's decision.
Requests are parsed strictly; anything outside the contract is a 400 invalid_request.
Callers are not authenticated: submitted_by_ref and reviewer_ref are declared.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    ValidationError,
)

from adapters.inbound.http.problems import OPAQUE_REF, first_error, problem
from application.audit import AuditTrail
from application.hospital_approval import HospitalApplicationStore, ReviewerDirectory
from application.synchronization import (
    PatientGrantDirectory,
    RequestNotFound,
    RequestView,
    SynchronizationStore,
    decide_request,
    get_request,
    list_requests,
    submit_request,
)
from domain.hospital_approval import InvalidDecision, Outcome, ReviewerNotAllowed
from domain.synchronization import (
    MAX_DURATION_DAYS,
    Consent,
    ConsentBasis,
    InvalidSynchronizationRequest,
    NotPending,
    RequestStatus,
    ScopeItem,
    SyncDecisionDraft,
    SynchronizationDecision,
    SynchronizationRequest,
)

NOTICE = (
    "Fictional demo synchronization requests, held in memory by the Governance Node: "
    "requests and decisions are lost on restart, requests are not authenticated, and "
    "patient grants are checked against fictional demo grants (MOCKED)."
)

Ref = Annotated[str, Field(pattern=OPAQUE_REF.pattern)]


def _unique(items: list[str]) -> list[str]:
    if len(set(items)) != len(items):
        raise ValueError("scope items must be unique")
    return items


ScopeField = Annotated[
    list[Literal["encounters", "medications", "lab_reports"]],
    Field(min_length=1),
    AfterValidator(_unique),
]


class ConsentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: Literal["patient_grant", "signed_consent_form", "emergency_override", "none"]
    access_grant_ref: Ref | None


class NewRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requester_organization_ref: Ref
    submitted_by_ref: Ref
    target_organization_ref: Ref
    patient_ref: Ref
    purpose: Annotated[str, Field(min_length=1, max_length=200)]
    scope: ScopeField
    duration_days: Annotated[StrictInt, Field(ge=1, le=MAX_DURATION_DAYS)]
    consent: ConsentBody


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer_ref: Ref
    outcome: Literal["approved", "rejected"]
    rationale: Annotated[str, Field(max_length=2000)]
    conditions: Annotated[
        list[Annotated[str, Field(max_length=500)]], Field(max_length=10)
    ]
    approved_days: StrictInt | None
    manual_checks_confirmed: StrictBool


def _scope(scope: frozenset[ScopeItem]) -> list[str]:
    # In the contract's order.
    return [item.value for item in ScopeItem if item in scope]


def _time(at: datetime | None) -> str | None:
    return at.isoformat() if at else None


def _summary(
    request: SynchronizationRequest,
    decision: SynchronizationDecision | None,
    status: RequestStatus,
) -> dict:
    return {
        "request_ref": request.request_ref,
        "requester_organization_ref": request.requester_organization_ref,
        "target_organization_ref": request.target_organization_ref,
        "patient_ref": request.patient_ref,
        "status": status.value,
        "submitted_at": request.submitted_at.isoformat(),
        "decision_ref": request.decision_ref,
        "valid_until": _time(decision.valid_until) if decision else None,
    }


def _decision(decision: SynchronizationDecision) -> dict:
    return {
        "decision_ref": decision.decision_ref,
        "request_ref": decision.request_ref,
        "outcome": decision.outcome.value,
        "decided_by_ref": decision.decided_by_ref,
        "decided_at": decision.decided_at.isoformat(),
        "rationale": decision.rationale,
        "conditions": list(decision.conditions),
        "approved_days": decision.approved_days,
        "valid_until": _time(decision.valid_until),
    }


def _detail(view: RequestView) -> dict:
    request = view.request
    return {
        **_summary(request, view.decision, view.status),
        "submitted_by_ref": request.submitted_by_ref,
        "purpose": request.purpose,
        "scope": _scope(request.scope),
        "duration_days": request.duration_days,
        "consent": {
            "basis": request.consent.basis.value,
            "access_grant_ref": request.consent.access_grant_ref,
        },
        "checks": [
            {"check": c.check, "state": c.state.value, "detail": c.detail}
            for c in view.checks
        ],
        "max_approved_days": view.max_approved_days,
        "decision": _decision(view.decision) if view.decision else None,
    }


def _invalid(detail: str) -> JSONResponse:
    return problem(400, "Invalid request", "invalid_request", detail)


def _not_found(request_ref: str) -> JSONResponse:
    return problem(
        404,
        "Request not found",
        "request_not_found",
        f"No synchronization request {request_ref}.",
    )


def create_router(
    store: SynchronizationStore,
    reviewers: ReviewerDirectory,
    grants: PatientGrantDirectory,
    applications: HospitalApplicationStore,
    audit: AuditTrail,
    clock: Callable[[], datetime],
) -> APIRouter:
    router = APIRouter(prefix="/v1/synchronization-requests", tags=["synchronization"])

    def view(request_ref: str) -> RequestView:
        return get_request(request_ref, store, grants, applications, clock)

    @router.get("")
    def list_synchronization_requests(status: str | None = None) -> JSONResponse:
        try:
            wanted = RequestStatus(status) if status is not None else None
        except ValueError:
            allowed = ", ".join(s.value for s in RequestStatus)
            return _invalid(f"status must be one of: {allowed}")
        rows = list_requests(store, clock(), wanted)
        return JSONResponse(
            {"notice": NOTICE, "requests": [_summary(*row) for row in rows]}
        )

    @router.post("")
    async def submit_synchronization_request(request: Request) -> JSONResponse:
        try:
            body = NewRequestBody.model_validate_json(await request.body())
        except ValidationError as error:
            return _invalid(first_error(error))
        try:
            submitted = submit_request(
                requester_organization_ref=body.requester_organization_ref,
                submitted_by_ref=body.submitted_by_ref,
                target_organization_ref=body.target_organization_ref,
                patient_ref=body.patient_ref,
                purpose=body.purpose,
                scope=frozenset(ScopeItem(item) for item in body.scope),
                duration_days=body.duration_days,
                consent=Consent(
                    ConsentBasis(body.consent.basis), body.consent.access_grant_ref
                ),
                store=store,
                audit=audit,
                clock=clock,
            )
        except InvalidSynchronizationRequest as error:
            return _invalid(str(error))
        return JSONResponse(_detail(view(submitted.request_ref)), status_code=201)

    @router.get("/{request_ref}")
    def get_synchronization_request(request_ref: str) -> JSONResponse:
        try:
            return JSONResponse(_detail(view(request_ref)))
        except RequestNotFound:
            return _not_found(request_ref)

    @router.post("/{request_ref}/decision")
    async def decide_synchronization_request(
        request_ref: str, request: Request
    ) -> JSONResponse:
        if store.request(request_ref) is None:
            return _not_found(request_ref)
        try:
            body = DecisionBody.model_validate_json(await request.body())
        except ValidationError as error:
            return _invalid(first_error(error))
        draft = SyncDecisionDraft(
            outcome=Outcome(body.outcome),
            rationale=body.rationale,
            conditions=tuple(body.conditions),
            approved_days=body.approved_days,
            manual_checks_confirmed=body.manual_checks_confirmed,
        )
        try:
            decision = decide_request(
                request_ref,
                body.reviewer_ref,
                draft,
                store,
                reviewers,
                grants,
                applications,
                audit,
                clock,
            )
        except RequestNotFound:
            return _not_found(request_ref)
        except NotPending as error:
            return problem(409, "Not pending", "not_pending", str(error))
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

    return router
