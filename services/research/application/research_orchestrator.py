"""Application-owned orchestration port and D2 mock implementation."""

from dataclasses import asdict
from typing import Protocol

from domain.research_job import JobStatus, ResearchJob, Stage


class JobStore(Protocol):
    def get(self, job_ref: str) -> ResearchJob | None: ...

    def put(self, job: ResearchJob) -> None: ...


class MockJobStore:
    def __init__(self) -> None:
        self.jobs: dict[str, ResearchJob] = {}

    def get(self, job_ref: str) -> ResearchJob | None:
        return self.jobs.get(job_ref)

    def put(self, job: ResearchJob) -> None:
        self.jobs[job.job_ref] = job


class ResearchOrchestrator:
    """Coordinates mocked node executions without reading hospital storage."""

    def __init__(self, store: JobStore | None = None) -> None:
        self.store = store or MockJobStore()

    def submit(
        self,
        *,
        job_ref: str,
        project_ref: str,
        authorization_decision_ref: str,
        requested_by: str,
        target_organizations: list[str],
    ) -> ResearchJob:
        existing = self.store.get(job_ref)
        if existing:
            return existing
        job = ResearchJob(
            job_ref=job_ref,
            project_ref=project_ref,
            authorization_decision_ref=authorization_decision_ref,
            requested_by=requested_by,
            stages=[
                Stage(f"{job_ref}-auth", "authorization_check", "org-governance"),
                *[
                    Stage(
                        f"{job_ref}-exec-{organization[-1]}", "execution", organization
                    )
                    for organization in target_organizations
                ],
                Stage(f"{job_ref}-agg", "aggregation", "org-platform"),
                Stage(f"{job_ref}-validation", "output_validation", "org-platform"),
            ],
        )
        if authorization_decision_ref != "dec-rar-001":
            job.status = JobStatus.DENIED
            job.error = {
                "code": "authorization_denied",
                "message": "The mocked Governance decision was not accepted.",
                "retryable": False,
            }
            for stage in job.stages:
                stage.status = stage.status.DENIED
        self.store.put(job)
        return job

    def read(self, job_ref: str) -> ResearchJob | None:
        job = self.store.get(job_ref)
        if job:
            job.advance()
        return job


def serialize(job: ResearchJob) -> dict:
    document = asdict(job)
    document["status"] = job.status.value
    for stage in document["stages"]:
        stage["status"] = stage["status"].value
    document["mocked"] = True
    return document
