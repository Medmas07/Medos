from datetime import date, datetime
import re
from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from application.research_execution_agent import (
    ExecutionConflictError,
    ExecutionNotFoundError,
    ResearchAuthorizationError,
    ResearchExecutionAgent,
)
from domain.research_execution import ResearchExecutionRequest

REF_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$"
NAME_PATTERN = r"^[a-z][a-z0-9_]*$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Target(StrictModel):
    node_ref: str = Field(min_length=1, max_length=100, pattern=REF_PATTERN)
    organization_ref: str = Field(min_length=1, max_length=100, pattern=REF_PATTERN)


class Requester(StrictModel):
    organization_ref: str = Field(min_length=1, max_length=100, pattern=REF_PATTERN)
    actor_ref: str = Field(min_length=1, max_length=100, pattern=REF_PATTERN)


class Authorization(StrictModel):
    decision_ref: str = Field(min_length=1, max_length=100, pattern=REF_PATTERN)
    authority_organization_ref: str = Field(
        min_length=1, max_length=100, pattern=REF_PATTERN
    )
    valid_until: datetime
    approved_organization_refs: list[str] = Field(min_length=1)
    approved_variables: list[str] = Field(min_length=1)

    @field_validator("approved_organization_refs")
    @classmethod
    def valid_organizations(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("values must be unique")
        if not all(re.fullmatch(REF_PATTERN, value) for value in values):
            raise ValueError("values must be references")
        return values

    @field_validator("approved_variables")
    @classmethod
    def valid_approved_variables(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("values must be unique")
        if not all(re.fullmatch(NAME_PATTERN, value) for value in values):
            raise ValueError("values must be names")
        return values


class Population(StrictModel):
    age_min: int | None = Field(default=None, ge=0, le=130)
    age_max: int | None = Field(default=None, ge=0, le=130)
    encounter_from: date | None = None
    encounter_to: date | None = None

    @model_validator(mode="after")
    def at_least_one_criterion(self):
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("population requires at least one criterion")
        if self.age_min is not None and self.age_max is not None:
            if self.age_min > self.age_max:
                raise ValueError("age_min must not exceed age_max")
        if self.encounter_from and self.encounter_to:
            if self.encounter_from > self.encounter_to:
                raise ValueError("encounter_from must not exceed encounter_to")
        return self


class DataScope(StrictModel):
    population: Population
    variables: list[str] = Field(min_length=1)

    @field_validator("variables")
    @classmethod
    def unique_variables(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("variables must be unique")
        if not all(re.fullmatch(NAME_PATTERN, value) for value in values):
            raise ValueError("variables must be names")
        return values


class Algorithm(StrictModel):
    language: Literal["python"]
    artifact_ref: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern="^[a-f0-9]{64}$")
    entrypoint: str = Field(pattern="^[A-Za-z_][A-Za-z0-9_]{0,99}$")


class OutputPolicy(StrictModel):
    kind: Literal["aggregate_table"]
    minimum_cell_size: int = Field(ge=1)
    require_disclosure_review: Literal[True]


class SubmitExecution(StrictModel):
    execution_id: str = Field(min_length=1, max_length=100, pattern=REF_PATTERN)
    job_ref: str = Field(min_length=1, max_length=100, pattern=REF_PATTERN)
    project_ref: str = Field(min_length=1, max_length=100, pattern=REF_PATTERN)
    target: Target
    submitted_by: Requester
    purpose: str = Field(min_length=1, max_length=500)
    authorization: Authorization
    data_scope: DataScope
    algorithm: Algorithm
    output_policy: OutputPolicy


def create_router(agent: ResearchExecutionAgent, clock) -> APIRouter:
    router = APIRouter(prefix="/v1/research-executions", tags=["research"])

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    async def submit_execution(request: Request):
        try:
            payload = await request.json()
            parsed = SubmitExecution.model_validate(payload)
        except (ValueError, ValidationError):
            return _problem(400, "invalid_request", "The request is invalid.")
        now = clock()
        domain_request = ResearchExecutionRequest(**parsed.model_dump(mode="json"))
        try:
            execution = agent.submit(domain_request, now)
        except ResearchAuthorizationError as error:
            return _problem(403, error.code, "The node denied this execution.")
        except ExecutionConflictError:
            return _problem(409, "execution_conflict", "The execution id is in use.")
        return {
            "execution_id": domain_request.execution_id,
            "job_ref": domain_request.job_ref,
            "node_ref": execution.node_ref,
            "status": "accepted",
            "accepted_at": execution.updated_at.isoformat(),
            "mocked": execution.mocked,
        }

    @router.get("/{execution_id}")
    def get_execution(execution_id: str):
        if (
            not execution_id
            or len(execution_id) > 100
            or not re.fullmatch(REF_PATTERN, execution_id)
        ):
            return _problem(400, "invalid_request", "The request is invalid.")
        try:
            return _serialize(agent.get(execution_id))
        except ExecutionNotFoundError:
            return _problem(404, "execution_not_found", "The execution was not found.")

    return router


def _serialize(execution) -> dict:
    document = {
        "execution_id": execution.request.execution_id,
        "job_ref": execution.request.job_ref,
        "node_ref": execution.node_ref,
        "organization_ref": execution.organization_ref,
        "status": execution.status.value,
        "updated_at": execution.updated_at.isoformat(),
        "mocked": execution.mocked,
    }
    if execution.result is not None:
        document["result"] = execution.result
    if execution.error is not None:
        document["error"] = {
            "code": execution.error.code,
            "message": execution.error.message,
            "retryable": execution.error.retryable,
        }
    return document


def _problem(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={"code": code, "message": message, "retryable": False},
    )
