"""contracts/api/governance/research-requests.v1.yaml (HC-133).

Submits, lists, and reads research access requests, and records a reviewer's decision.
Requests are parsed strictly; anything outside the contract is a 400 invalid_request.
submitted_by_ref is declared. With authentication required (HC-211), a decision needs a
bearer session and reviewer_ref must be the signed-in person; off, it is declared.
"""

from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
)

from adapters.inbound.http.authentication import ReviewerAuthentication
from adapters.inbound.http.problems import OPAQUE_REF, first_error, problem
from application.audit import AuditTrail
from application.hospital_approval import HospitalApplicationStore, ReviewerDirectory
from application.ledger import AuditLedgerPort
from application.research import (
    RequestNotFound,
    RequestView,
    ResearchStore,
    decide_request,
    get_request,
    list_requests,
    submit_request,
)
from domain.policy import PolicyHistory
from domain.hospital_approval import InvalidDecision, Outcome, ReviewerNotAllowed
from domain.research import (
    DataScope,
    InvalidResearchRequest,
    NotUnderReview,
    Population,
    RequestStatus,
    ResearchDecision,
    ResearchDecisionDraft,
    ResearchRequest,
)

NOTICE = (
    "Fictional demo research access requests, held in memory by the Governance Node: "
    "requests and decisions are lost on restart, and requests are not authenticated."
)

Ref = Annotated[str, Field(pattern=OPAQUE_REF.pattern)]
Variable = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,99}$")]
Age = Annotated[StrictInt, Field(ge=0, le=130)]


def unique_items(items: list) -> list:
    if len(set(items)) != len(items):
        raise ValueError("items must be unique")
    return items


class PopulationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_min: Age | None = None
    age_max: Age | None = None
    encounter_from: date | None = None
    encounter_to: date | None = None


class DataScopeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    population: PopulationBody
    variables: Annotated[
        list[Variable], Field(min_length=1), AfterValidator(unique_items)
    ]


class NewRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_ref: Ref
    project_title: Annotated[str, Field(min_length=1, max_length=200)]
    research_organization_ref: Ref
    principal_investigator_ref: Ref
    submitted_by_ref: Ref
    purpose: Annotated[str, Field(min_length=1, max_length=500)]
    participating_organization_refs: Annotated[
        list[Ref], Field(min_length=1), AfterValidator(unique_items)
    ]
    data_scope: DataScopeBody
    protocol_document_ref: Ref | None


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer_ref: Ref
    outcome: Literal["approved", "rejected"]
    rationale: Annotated[str, Field(max_length=2000)]
    conditions: Annotated[
        list[Annotated[str, Field(max_length=500)]], Field(max_length=10)
    ]
    approved_organization_refs: list[Ref] | None
    approved_variables: list[Variable] | None
    validity_months: StrictInt | None
    minimum_cell_size: StrictInt | None


def to_population(body: PopulationBody) -> Population:
    return Population(
        body.age_min, body.age_max, body.encounter_from, body.encounter_to
    )


def population_wire(population: Population) -> dict:
    wire = {
        "age_min": population.age_min,
        "age_max": population.age_max,
        "encounter_from": population.encounter_from.isoformat()
        if population.encounter_from
        else None,
        "encounter_to": population.encounter_to.isoformat()
        if population.encounter_to
        else None,
    }
    return {key: value for key, value in wire.items() if value is not None}


def _time(at: datetime | None) -> str | None:
    return at.isoformat() if at else None


def _summary(
    request: ResearchRequest, decision: ResearchDecision | None, status: RequestStatus
) -> dict:
    return {
        "request_ref": request.request_ref,
        "project_ref": request.project_ref,
        "research_organization_ref": request.research_organization_ref,
        "principal_investigator_ref": request.principal_investigator_ref,
        "status": status.value,
        "submitted_at": request.submitted_at.isoformat(),
        "decision_ref": request.decision_ref,
        "valid_until": _time(decision.valid_until) if decision else None,
    }


def _decision(decision: ResearchDecision) -> dict:
    return {
        "decision_ref": decision.decision_ref,
        "request_ref": decision.request_ref,
        "outcome": decision.outcome.value,
        "decided_by_ref": decision.decided_by_ref,
        "decided_at": decision.decided_at.isoformat(),
        "policy_ref": decision.policy_ref,
        "rationale": decision.rationale,
        "conditions": list(decision.conditions),
        "approved_organization_refs": list(decision.approved_organization_refs),
        "approved_variables": list(decision.approved_variables),
        "minimum_cell_size": decision.minimum_cell_size,
        "valid_until": _time(decision.valid_until),
    }


def _detail(view: RequestView) -> dict:
    request = view.request
    return {
        **_summary(request, view.decision, view.status),
        "project_title": request.project_title,
        "submitted_by_ref": request.submitted_by_ref,
        "purpose": request.purpose,
        "participating_organization_refs": list(
            request.participating_organization_refs
        ),
        "data_scope": {
            "population": population_wire(request.data_scope.population),
            "variables": list(request.data_scope.variables),
        },
        "protocol_document_ref": request.protocol_document_ref,
        "checks": [
            {"check": c.check, "state": c.state.value, "detail": c.detail}
            for c in view.checks
        ],
        "eligible_organization_refs": list(view.eligible_organization_refs),
        "decision": _decision(view.decision) if view.decision else None,
    }


def _invalid(detail: str) -> JSONResponse:
    return problem(400, "Invalid request", "invalid_request", detail)


def _not_found(request_ref: str) -> JSONResponse:
    return problem(
        404,
        "Request not found",
        "request_not_found",
        f"No research access request {request_ref}.",
    )


def _tuple(values: list[str] | None) -> tuple[str, ...] | None:
    return tuple(values) if values is not None else None


def create_router(
    store: ResearchStore,
    reviewers: ReviewerDirectory,
    applications: HospitalApplicationStore,
    policies: PolicyHistory,
    audit: AuditTrail,
    clock: Callable[[], datetime],
    ledger: AuditLedgerPort,
    auth: ReviewerAuthentication,
) -> APIRouter:
    router = APIRouter(prefix="/v1/research-requests", tags=["research"])

    def view(request_ref: str) -> RequestView:
        return get_request(request_ref, store, applications, clock)

    @router.get("")
    def list_research_requests(status: str | None = None) -> JSONResponse:
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
    async def submit_research_request(request: Request) -> JSONResponse:
        try:
            body = NewRequestBody.model_validate_json(await request.body())
        except ValidationError as error:
            return _invalid(first_error(error))

        def build(request_ref: str, now: datetime) -> ResearchRequest:
            return ResearchRequest(
                request_ref=request_ref,
                project_ref=body.project_ref,
                project_title=body.project_title.strip(),
                research_organization_ref=body.research_organization_ref,
                principal_investigator_ref=body.principal_investigator_ref,
                submitted_by_ref=body.submitted_by_ref,
                purpose=body.purpose.strip(),
                participating_organization_refs=tuple(
                    body.participating_organization_refs
                ),
                data_scope=DataScope(
                    to_population(body.data_scope.population),
                    tuple(body.data_scope.variables),
                ),
                protocol_document_ref=body.protocol_document_ref,
                submitted_at=now,
            )

        try:
            submitted = submit_request(build, store, audit, clock)
        except InvalidResearchRequest as error:
            return _invalid(str(error))
        return JSONResponse(_detail(view(submitted.request_ref)), status_code=201)

    @router.get("/{request_ref}")
    def get_research_request(request_ref: str) -> JSONResponse:
        try:
            return JSONResponse(_detail(view(request_ref)))
        except RequestNotFound:
            return _not_found(request_ref)

    @router.post("/{request_ref}/decision")
    async def decide_research_request(
        request_ref: str, request: Request
    ) -> JSONResponse:
        caller = auth.caller(request)
        if isinstance(caller, JSONResponse):
            return caller
        if store.request(request_ref) is None:
            return _not_found(request_ref)
        try:
            body = DecisionBody.model_validate_json(await request.body())
        except ValidationError as error:
            return _invalid(first_error(error))
        if (refused := auth.refuse(caller, body.reviewer_ref)) is not None:
            return refused
        draft = ResearchDecisionDraft(
            outcome=Outcome(body.outcome),
            rationale=body.rationale,
            conditions=tuple(body.conditions),
            approved_organization_refs=_tuple(body.approved_organization_refs),
            approved_variables=_tuple(body.approved_variables),
            validity_months=body.validity_months,
            minimum_cell_size=body.minimum_cell_size,
        )
        try:
            decision = decide_request(
                request_ref,
                body.reviewer_ref,
                draft,
                store,
                reviewers,
                applications,
                policies,
                audit,
                clock,
                ledger,
            )
        except RequestNotFound:
            return _not_found(request_ref)
        except NotUnderReview as error:
            return problem(409, "Not under review", "not_under_review", str(error))
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
