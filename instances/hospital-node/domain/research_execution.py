"""Hospital-local Compute-to-Data execution values (HC-183)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class ResearchExecutionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ResearchSubject:
    """Minimal local facts used by the installed aggregate; never serialized."""

    patient_ref: str
    encounter_dates: tuple[date, ...]
    hba1c_values: tuple[float, ...]


@dataclass(frozen=True)
class ResearchExecutionRequest:
    execution_id: str
    job_ref: str
    project_ref: str
    target: dict
    submitted_by: dict
    purpose: str
    authorization: dict
    data_scope: dict
    algorithm: dict
    output_policy: dict

    def immutable_input(self) -> tuple:
        return (
            self.job_ref,
            self.project_ref,
            _freeze(self.target),
            _freeze(self.submitted_by),
            self.purpose,
            _freeze(self.authorization),
            _freeze(self.data_scope),
            _freeze(self.algorithm),
            _freeze(self.output_policy),
        )


@dataclass(frozen=True)
class ExecutionProblem:
    code: str
    message: str
    retryable: bool


@dataclass
class ResearchExecution:
    request: ResearchExecutionRequest
    node_ref: str
    organization_ref: str
    status: ResearchExecutionStatus
    updated_at: datetime
    mocked: bool
    result: dict | None = None
    error: ExecutionProblem | None = None


def _freeze(value):
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value
