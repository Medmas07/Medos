"""Framework-free research job model and deterministic D2 state rules."""

from dataclasses import dataclass, field
from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    DENIED = "denied"
    FAILED = "failed"


class StageStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"


@dataclass
class Stage:
    id: str
    stage: str
    organization_ref: str
    status: StageStatus = StageStatus.QUEUED
    progress: int = 0
    error_code: str | None = None


@dataclass
class ResearchJob:
    job_ref: str
    project_ref: str
    authorization_decision_ref: str
    requested_by: str
    status: JobStatus = JobStatus.QUEUED
    poll_count: int = 0
    stages: list[Stage] = field(default_factory=list)
    execution_refs: dict[str, str] = field(default_factory=dict)
    result: dict | None = None
    error: dict | None = None

    def advance(self) -> None:
        """Advance one deterministic demo tick; no real execution occurs."""
        self.poll_count += 1
        if is_terminal(self.status):
            return
        if self.poll_count == 1:
            self.status = JobStatus.RUNNING
            self.stages[0].status = StageStatus.COMPLETED
            self.stages[0].progress = 100
            for stage in self.stages[1:3]:
                stage.status = StageStatus.RUNNING
                stage.progress = 45
            return
        if self.job_ref == "job-failed":
            self.status = JobStatus.FAILED
            self.stages[-1].status = StageStatus.FAILED
            self.stages[-1].error_code = "execution_failed"
            self.error = {
                "code": "execution_failed",
                "message": "The mocked distributed execution did not complete.",
                "retryable": True,
            }
            return
        self.status = JobStatus.COMPLETED
        for stage in self.stages:
            stage.status = StageStatus.COMPLETED
            stage.progress = 100
        self.result = controlled_result(self)


def is_terminal(status: JobStatus) -> bool:
    return status in {JobStatus.COMPLETED, JobStatus.DENIED, JobStatus.FAILED}


def controlled_result(job: ResearchJob) -> dict:
    if job.job_ref == "job-empty":
        return {
            "outcome": "empty",
            "columns": ["age_band", "participant_count"],
            "rows": [],
            "disclosure": {"status": "passed", "minimum_cell_size": 10},
        }
    return {
        "outcome": "released",
        "columns": ["age_band", "participant_count", "hba1c_above_7_pct"],
        "rows": [["40-49", 212, 18.4], ["50-59", 305, 26.9]],
        "disclosure": {"status": "passed", "minimum_cell_size": 10},
    }
