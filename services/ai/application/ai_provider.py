from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from domain.advisory_output import AdvisoryOutput


class AiTask(Enum):
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    EXPLANATION = "explanation"


@dataclass(frozen=True)
class AiRequest:
    request_id: str
    task: AiTask
    instructions: str
    input_text: str


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    model_id: str
    is_mock: bool
    supported_tasks: frozenset[AiTask]


class AiProviderErrorKind(Enum):
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_TASK = "unsupported_task"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"


class AiProviderError(Exception):
    def __init__(self, kind: AiProviderErrorKind, message: str):
        super().__init__(message)
        self.kind = kind


class AiProvider(Protocol):
    """Provider-neutral port. Adapters wrap one model provider and raise only AiProviderError."""

    def describe(self) -> ProviderDescriptor: ...

    def generate(self, request: AiRequest) -> AdvisoryOutput: ...
