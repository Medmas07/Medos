"""Hospital-side research execution use case and owned ports (HC-183)."""

from datetime import UTC, datetime
from typing import Protocol

from domain.node_identity import NodeIdentity
from domain.research_execution import (
    ExecutionProblem,
    ResearchExecution,
    ResearchExecutionRequest,
    ResearchExecutionStatus,
)


class ResearchExecutionStore(Protocol):
    def get(self, execution_id: str) -> ResearchExecution | None: ...

    def put(self, execution: ResearchExecution) -> None: ...


class LocalResearchExecutor(Protocol):
    mocked: bool

    def execute(self, request: ResearchExecutionRequest, now: datetime) -> dict: ...


class ExecutionConflictError(ValueError):
    pass


class ExecutionNotFoundError(LookupError):
    pass


class LocalExecutionError(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class ResearchAuthorizationError(PermissionError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ResearchExecutionAgent:
    def __init__(
        self,
        identity: NodeIdentity,
        executor: LocalResearchExecutor,
        store: ResearchExecutionStore,
    ) -> None:
        self.identity = identity
        self.executor = executor
        self.store = store

    def submit(
        self, request: ResearchExecutionRequest, now: datetime
    ) -> ResearchExecution:
        existing = self.store.get(request.execution_id)
        if existing:
            if existing.request.immutable_input() != request.immutable_input():
                raise ExecutionConflictError(request.execution_id)
            return existing

        self._authorize(request, now)
        try:
            result = self.executor.execute(request, now)
            execution = ResearchExecution(
                request=request,
                node_ref=self.identity.node_ref,
                organization_ref=self.identity.organization_ref,
                status=ResearchExecutionStatus.COMPLETED,
                updated_at=now,
                mocked=self.executor.mocked,
                result=result,
            )
        except LocalExecutionError as error:
            execution = ResearchExecution(
                request=request,
                node_ref=self.identity.node_ref,
                organization_ref=self.identity.organization_ref,
                status=ResearchExecutionStatus.FAILED,
                updated_at=now,
                mocked=self.executor.mocked,
                error=ExecutionProblem(error.code, error.message, error.retryable),
            )
        except Exception:
            execution = ResearchExecution(
                request=request,
                node_ref=self.identity.node_ref,
                organization_ref=self.identity.organization_ref,
                status=ResearchExecutionStatus.FAILED,
                updated_at=now,
                mocked=self.executor.mocked,
                error=ExecutionProblem(
                    "execution_failed",
                    "The installed local research execution did not complete.",
                    False,
                ),
            )
        self.store.put(execution)
        return execution

    def get(self, execution_id: str) -> ResearchExecution:
        execution = self.store.get(execution_id)
        if execution is None:
            raise ExecutionNotFoundError(execution_id)
        return execution

    def _authorize(self, request: ResearchExecutionRequest, now: datetime) -> None:
        target = request.target
        authorization = request.authorization
        if (
            authorization["authority_organization_ref"] != "org-governance"
            or not authorization["decision_ref"]
        ):
            raise ResearchAuthorizationError("authorization_denied")
        if (
            target["node_ref"] != self.identity.node_ref
            or target["organization_ref"] != self.identity.organization_ref
            or self.identity.organization_ref
            not in authorization["approved_organization_refs"]
        ):
            raise ResearchAuthorizationError("scope_denied")
        requested_variables = set(request.data_scope["variables"])
        if not requested_variables <= set(authorization["approved_variables"]):
            raise ResearchAuthorizationError("scope_denied")
        valid_until = datetime.fromisoformat(authorization["valid_until"])
        if valid_until.tzinfo is None or valid_until <= now.astimezone(UTC):
            raise ResearchAuthorizationError("authorization_expired")
