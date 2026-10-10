"""Framework-free research job state and boundary values."""

from dataclasses import dataclass, field
from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    AUTHORIZING = "authorizing"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    COMPLETED = "completed"
    DENIED = "denied"
    FAILED = "failed"


class ExecutionStatus(StrEnum):
    ACCEPTED = "accepted"
    AUTHORIZATION_CHECK = "authorization_check"
    QUEUED = "queued"
    RUNNING = "running"
    OUTPUT_REVIEW = "output_review"
    COMPLETED = "completed"
    DENIED = "denied"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(frozen=True)
class JobError:
    code: str
    message: str
    retryable: bool


@dataclass(frozen=True)
class AuthorizationDecision:
    decision_ref: str
    approved: bool
    approved_organization_refs: tuple[str, ...] = ()
    approved_variables: tuple[str, ...] = ()
    authority_organization_ref: str = "org-governance"
    valid_until: str | None = None
    reason_code: str | None = None


@dataclass
class NodeExecution:
    execution_id: str
    organization_ref: str
    status: ExecutionStatus
    result: dict | None = None
    error: JobError | None = None


@dataclass
class ResearchJob:
    job_ref: str
    project_ref: str
    authorization_decision_ref: str
    requested_by: str
    purpose: str
    target_organizations: tuple[str, ...]
    data_scope: dict
    algorithm: dict
    output_policy: dict
    status: JobStatus = JobStatus.QUEUED
    executions: list[NodeExecution] = field(default_factory=list)
    error: JobError | None = None

    def matches_request(self, other: "ResearchJob") -> bool:
        fields = (
            "project_ref",
            "authorization_decision_ref",
            "requested_by",
            "purpose",
            "target_organizations",
            "data_scope",
            "algorithm",
            "output_policy",
        )
        return all(getattr(self, name) == getattr(other, name) for name in fields)

    def mark_denied(self, reason_code: str | None = None) -> None:
        self.status = JobStatus.DENIED
        self.error = JobError(
            code=reason_code or "authorization_denied",
            message="Governance did not authorize this research job.",
            retryable=False,
        )

    def refresh_status(self) -> None:
        if not self.executions:
            self.status = JobStatus.FAILED
            self.error = JobError(
                "dispatch_failed",
                "No Hospital Node accepted the research job.",
                True,
            )
            return
        statuses = {execution.status for execution in self.executions}
        error_statuses = {
            ExecutionStatus.DENIED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.EXPIRED,
        }
        if statuses <= {ExecutionStatus.COMPLETED}:
            self.status = JobStatus.COMPLETED
        elif statuses & error_statuses and statuses <= {
            ExecutionStatus.COMPLETED,
            *error_statuses,
        }:
            self.status = JobStatus.FAILED
            self.error = JobError(
                "node_execution_failed",
                "At least one Hospital Node did not return a controlled result.",
                any(
                    execution.error and execution.error.retryable
                    for execution in self.executions
                ),
            )
        else:
            self.status = JobStatus.RUNNING


def is_terminal(status: JobStatus) -> bool:
    return status in {JobStatus.COMPLETED, JobStatus.DENIED, JobStatus.FAILED}
