"""D3 application orchestration over the Hospital Node execution port."""

from dataclasses import asdict
from typing import Protocol

from domain.research_job import JobStatus, ResearchJob, Stage, StageStatus
from application.hospital_node_execution import HospitalNodeExecutionPort


class JobStore(Protocol):
    def get(self, job_ref: str) -> ResearchJob | None: ...

    def put(self, job: ResearchJob) -> None: ...


class InMemoryJobStore:
    def __init__(self) -> None:
        self.jobs: dict[str, ResearchJob] = {}

    def get(self, job_ref: str) -> ResearchJob | None:
        return self.jobs.get(job_ref)

    def put(self, job: ResearchJob) -> None:
        self.jobs[job.job_ref] = job


class ResearchOrchestrator:
    """Coordinates mocked node executions without reading hospital storage."""

    def __init__(
        self,
        store: JobStore | None = None,
        node_execution: HospitalNodeExecutionPort | None = None,
        node_refs: list[str] | None = None,
    ) -> None:
        self.store = store or InMemoryJobStore()
        self.node_execution = node_execution
        self.node_refs = node_refs or []

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
        self.store.put(job)
        return job

    def read(self, job_ref: str) -> ResearchJob | None:
        job = self.store.get(job_ref)
        if job and self.node_execution:
            self._advance_over_nodes(job)
        elif job:
            job.advance()
        return job

    def _advance_over_nodes(self, job: ResearchJob) -> None:
        if job.poll_count == 0:
            job.poll_count = 1
            if not self.node_refs:
                job.status = JobStatus.FAILED
                job.error = {
                    "code": "node_not_configured",
                    "message": "No Hospital Node execution endpoint is configured.",
                    "retryable": False,
                }
                return
            job.status = JobStatus.RUNNING
            for node_ref, stage in zip(self.node_refs, job.stages[1:]):
                try:
                    response = self.node_execution.submit(
                        node_ref, self._request(job, node_ref)
                    )
                    response_status = response.get("status", "queued")
                    stage.status = (
                        StageStatus.RUNNING
                        if response_status == "accepted"
                        else StageStatus(response_status)
                    )
                    stage.progress = 45
                    job.execution_refs[node_ref] = response.get(
                        "execution_id", f"{job.job_ref}-{node_ref}"
                    )
                    if response.get("status") == "denied":
                        job.status = JobStatus.DENIED
                        job.error = {
                            "code": "authorization_denied",
                            "message": "A Hospital Node denied the execution.",
                            "retryable": False,
                        }
                        return
                except RuntimeError as exc:
                    job.status = JobStatus.FAILED
                    job.error = {
                        "code": "node_unavailable",
                        "message": str(exc),
                        "retryable": True,
                    }
                    return
            return
        if job.status is JobStatus.RUNNING:
            node_results = [
                self.node_execution.read(node_ref, execution_ref)
                for node_ref, execution_ref in job.execution_refs.items()
            ]
            if any(result.get("status") == "failed" for result in node_results):
                job.status = JobStatus.FAILED
                job.error = {
                    "code": "execution_failed",
                    "message": "A Hospital Node execution failed.",
                    "retryable": True,
                }
                return
            if any(result.get("status") == "denied" for result in node_results):
                job.status = JobStatus.DENIED
                job.error = {
                    "code": "authorization_denied",
                    "message": "A Hospital Node denied the execution.",
                    "retryable": False,
                }
                return
            if not all(result.get("status") == "completed" for result in node_results):
                return
            job.status = JobStatus.COMPLETED
            for stage in job.stages:
                stage.status = stage.status.COMPLETED
                stage.progress = 100
            job.result = {
                "outcome": "released",
                "source_node_refs": self.node_refs,
                "node_results": node_results,
            }

    @staticmethod
    def _request(job: ResearchJob, node_ref: str) -> dict:
        return {
            "execution_id": f"{job.job_ref}-{node_ref}",
            "job_ref": job.job_ref,
            "project_ref": job.project_ref,
            "target": {
                "node_ref": node_ref,
                "organization_ref": node_ref.replace("node-", "org-"),
            },
            "submitted_by": {
                "organization_ref": "org-platform",
                "actor_ref": job.requested_by,
            },
            "purpose": "Authorized research computation",
            "authorization": {
                "decision_ref": job.authorization_decision_ref,
                "authority_organization_ref": "org-governance",
                "valid_until": "2026-12-31T23:59:59+01:00",
                "approved_organization_refs": ["org-hospital-a", "org-hospital-b"],
                "approved_variables": ["age_band", "hba1c"],
            },
            "data_scope": {
                "population": {"age_min": 40, "age_max": 79},
                "variables": ["age_band", "hba1c"],
            },
            "algorithm": {
                "language": "python",
                "artifact_ref": "notebook://nb-001/cell/nb-001-cell-2",
                "sha256": "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801",
                "entrypoint": "compute",
            },
            "output_policy": {
                "kind": "aggregate_table",
                "minimum_cell_size": 10,
                "require_disclosure_review": True,
            },
        }


def serialize(job: ResearchJob) -> dict:
    document = asdict(job)
    document["status"] = job.status.value
    for stage in document["stages"]:
        stage["status"] = stage["status"].value
    return document
