"""Process-local execution state; durable persistence is outside HC-183."""

from domain.research_execution import ResearchExecution


class InMemoryResearchExecutionStore:
    def __init__(self) -> None:
        self._executions: dict[str, ResearchExecution] = {}

    def get(self, execution_id: str) -> ResearchExecution | None:
        return self._executions.get(execution_id)

    def put(self, execution: ResearchExecution) -> None:
        self._executions[execution.request.execution_id] = execution
