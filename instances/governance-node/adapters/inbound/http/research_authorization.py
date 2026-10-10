"""contracts/api/research/research-authorization-check.v1.yaml, provider side (HC-133).

Answers the Research Service's question before each Compute-to-Data job: does this
decision authorize this exact job now? A denial is a 200 result with a reason_code; an
unknown decision is a 404; only a check outside the contract is a 400. `purpose` is
accepted but not compared, and the decision's minimum cell size is not carried here.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

from adapters.inbound.http.problems import first_error, problem
from adapters.inbound.http.research_requests import (
    DataScopeBody,
    unique_items,
    to_population,
)
from application.audit import AuditTrail
from application.research import (
    DecisionNotFound,
    ResearchStore,
    check_research_authorization,
)
from domain.research import AUTHORITY_ORGANIZATION_REF, InvalidResearchRequest, JobAsk

# Ref of research-authorization-check.v1.yaml.
CheckRef = Annotated[str, Field(min_length=1, max_length=100)]


class AuthorizationCheckBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_ref: CheckRef
    project_ref: CheckRef
    requested_by: CheckRef
    purpose: Annotated[str, Field(min_length=1, max_length=500)]
    target_organization_refs: Annotated[
        list[CheckRef], Field(min_length=1), AfterValidator(unique_items)
    ]
    data_scope: DataScopeBody


def create_router(
    store: ResearchStore, audit: AuditTrail, clock: Callable[[], datetime]
) -> APIRouter:
    router = APIRouter(tags=["research"])

    @router.post("/v1/research-authorizations/check")
    async def check(request: Request) -> JSONResponse:
        try:
            body = AuthorizationCheckBody.model_validate_json(await request.body())
            population = to_population(body.data_scope.population)
        except ValidationError as error:
            return problem(
                400, "Invalid request", "invalid_request", first_error(error)
            )
        except InvalidResearchRequest as error:
            return problem(400, "Invalid request", "invalid_request", str(error))
        ask = JobAsk(
            project_ref=body.project_ref,
            requested_by=body.requested_by,
            purpose=body.purpose,
            target_organization_refs=frozenset(body.target_organization_refs),
            population=population,
            variables=frozenset(body.data_scope.variables),
        )
        try:
            answer = check_research_authorization(
                body.decision_ref, ask, store, audit, clock
            )
        except DecisionNotFound:
            return problem(
                404,
                "Decision not found",
                "decision_not_found",
                f"No research access decision {body.decision_ref}.",
            )
        decision = answer.decision
        result = {
            "decision_ref": decision.decision_ref,
            "status": "approved" if answer.approved else "denied",
            "approved_organization_refs": list(decision.approved_organization_refs)
            if answer.approved
            else [],
            "approved_variables": list(decision.approved_variables)
            if answer.approved
            else [],
            "authority_organization_ref": AUTHORITY_ORGANIZATION_REF,
        }
        if decision.valid_until:
            result["valid_until"] = decision.valid_until.isoformat()
        if answer.reason:
            result["reason_code"] = answer.reason.value
        return JSONResponse(result)

    return router
