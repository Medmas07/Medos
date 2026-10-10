"""Application-owned ports and use cases for D3 research orchestration."""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Protocol

from domain.research_job import (
    AuthorizationDecision,
    ExecutionStatus,
    JobError,
    JobStatus,
    NodeExecution,
    ResearchJob,
    is_terminal,
)


class JobStore(Protocol):
    def get(self, job_ref: str) -> ResearchJob | None: ...

    def put(self, job: ResearchJob) -> None: ...


class JobConflictError(ValueError):
    """A job reference was reused for a different immutable request."""


class GovernanceAuthorizationPort(Protocol):
    def check(self, job: ResearchJob) -> AuthorizationDecision: ...


class HospitalExecutionPort(Protocol):
    def submit(
        self,
        job: ResearchJob,
        organization_ref: str,
        authorization: AuthorizationDecision,
    ) -> NodeExecution: ...

    def read(self, execution: NodeExecution) -> NodeExecution: ...


class InMemoryJobStore:
    """Process-local D3 state; persistence remains outside HC-182."""

    def __init__(self) -> None:
        self.jobs: dict[str, ResearchJob] = {}

    def get(self, job_ref: str) -> ResearchJob | None:
        return self.jobs.get(job_ref)

    def put(self, job: ResearchJob) -> None:
        self.jobs[job.job_ref] = job


class ResearchOrchestrator:
    def __init__(
        self,
        authorization: GovernanceAuthorizationPort,
        executions: HospitalExecutionPort,
        store: JobStore | None = None,
    ) -> None:
        self.authorization = authorization
        self.executions = executions
        self.store = store or InMemoryJobStore()

    def submit(self, job: ResearchJob) -> ResearchJob:
        existing = self.store.get(job.job_ref)
        if existing:
            if not existing.matches_request(job):
                raise JobConflictError(job.job_ref)
            return existing

        job.status = JobStatus.AUTHORIZING
        try:
            decision = self.authorization.check(job)
        except Exception:
            job.status = JobStatus.FAILED
            job.error = JobError(
                "governance_unavailable",
                "Governance authorization could not be verified.",
                True,
            )
            self.store.put(job)
            return job

        requested = set(job.target_organizations)
        approved = set(decision.approved_organization_refs)
        requested_variables = set(job.data_scope.get("variables", []))
        approved_variables = set(decision.approved_variables)
        if (
            not decision.approved
            or decision.decision_ref != job.authorization_decision_ref
            or not requested <= approved
            or not requested_variables <= approved_variables
        ):
            job.mark_denied(decision.reason_code)
            self.store.put(job)
            return job
        try:
            valid_until = datetime.fromisoformat(decision.valid_until or "")
            if valid_until.tzinfo is None or valid_until <= datetime.now(UTC):
                raise ValueError
        except ValueError:
            job.mark_denied("authorization_expired")
            self.store.put(job)
            return job

        job.status = JobStatus.DISPATCHING
        for organization_ref in job.target_organizations:
            try:
                job.executions.append(
                    self.executions.submit(job, organization_ref, decision)
                )
            except Exception:
                job.executions.append(
                    NodeExecution(
                        execution_id=f"{job.job_ref}:{organization_ref}",
                        organization_ref=organization_ref,
                        status=ExecutionStatus.FAILED,
                        error=JobError(
                            "node_unavailable",
                            "The Hospital Node could not accept the execution.",
                            True,
                        ),
                    )
                )
        job.refresh_status()
        self.store.put(job)
        return job

    def read(self, job_ref: str, *, refresh: bool = True) -> ResearchJob | None:
        job = self.store.get(job_ref)
        if job is None or not refresh or is_terminal(job.status):
            return job
        job.executions = [self._refresh(execution) for execution in job.executions]
        job.refresh_status()
        self.store.put(job)
        return job

    def _refresh(self, execution: NodeExecution) -> NodeExecution:
        if execution.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.DENIED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.EXPIRED,
        }:
            return execution
        try:
            return self.executions.read(execution)
        except Exception:
            return NodeExecution(
                execution_id=execution.execution_id,
                organization_ref=execution.organization_ref,
                status=ExecutionStatus.FAILED,
                error=JobError(
                    "node_unavailable",
                    "The Hospital Node execution status could not be read.",
                    True,
                ),
            )


def serialize(job: ResearchJob) -> dict:
    document = asdict(job)
    document["status"] = job.status.value
    for execution in document["executions"]:
        execution["status"] = execution["status"].value
        for optional in ("result", "error"):
            if execution[optional] is None:
                del execution[optional]
    if document["error"] is None:
        del document["error"]
    document["mocked"] = False
    return document
