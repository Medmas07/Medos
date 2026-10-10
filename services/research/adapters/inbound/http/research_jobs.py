from fastapi import APIRouter, HTTPException, status
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from application.research_orchestrator import (
    JobConflictError,
    ResearchOrchestrator,
    serialize,
)
from domain.research_job import ResearchJob


class Population(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_min: int | None = Field(default=None, ge=0, le=130)
    age_max: int | None = Field(default=None, ge=0, le=130)
    encounter_from: str | None = None
    encounter_to: str | None = None


class DataScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    population: Population
    variables: list[str] = Field(min_length=1)

    @field_validator("variables")
    @classmethod
    def unique_variables(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("variables must be unique")
        return values


class Algorithm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Literal["python"]
    artifact_ref: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern="^[a-f0-9]{64}$")
    entrypoint: str = Field(pattern="^[A-Za-z_][A-Za-z0-9_]{0,99}$")


class OutputPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["aggregate_table"]
    minimum_cell_size: int = Field(ge=1)
    require_disclosure_review: Literal[True]


class SubmitJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_ref: str = Field(min_length=1, max_length=100)
    project_ref: str = Field(min_length=1, max_length=100)
    authorization_decision_ref: str = Field(min_length=1, max_length=100)
    requested_by: str = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=500)
    target_organizations: list[str] = Field(min_length=1, max_length=20)
    data_scope: DataScope
    algorithm: Algorithm
    output_policy: OutputPolicy

    @field_validator("target_organizations")
    @classmethod
    def unique_targets(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("target organizations must be unique")
        return values


def create_router(orchestrator: ResearchOrchestrator) -> APIRouter:
    router = APIRouter(prefix="/v1/research-jobs", tags=["research"])

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def submit_job(request: SubmitJob) -> dict:
        job = ResearchJob(
            **request.model_dump(exclude={"target_organizations"}, mode="json"),
            target_organizations=tuple(request.target_organizations),
        )
        try:
            return serialize(orchestrator.submit(job))
        except JobConflictError as error:
            raise HTTPException(
                status_code=409, detail="research_job_ref_conflict"
            ) from error

    @router.get("/{job_ref}")
    def get_job(job_ref: str, refresh: bool = True) -> dict:
        job = orchestrator.read(job_ref, refresh=refresh)
        if job is None:
            raise HTTPException(status_code=404, detail="research_job_not_found")
        return serialize(job)

    return router
