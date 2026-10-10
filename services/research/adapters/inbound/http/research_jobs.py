from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from application.research_orchestrator import ResearchOrchestrator, serialize


class SubmitJob(BaseModel):
    job_ref: str = Field(min_length=1, max_length=100)
    project_ref: str = Field(min_length=1, max_length=100)
    authorization_decision_ref: str = Field(min_length=1, max_length=100)
    requested_by: str = Field(min_length=1, max_length=100)
    target_organizations: list[str] = Field(min_length=1, max_length=3)


router = APIRouter(prefix="/v1/research-jobs", tags=["research"])
orchestrator = ResearchOrchestrator()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def submit_job(request: SubmitJob) -> dict:
    job = orchestrator.submit(**request.model_dump())
    return serialize(job)


@router.get("/{job_ref}")
def get_job(job_ref: str) -> dict:
    job = orchestrator.read(job_ref)
    if job is None:
        raise HTTPException(status_code=404, detail="research_job_not_found")
    return serialize(job)
