from collections.abc import Callable
from datetime import UTC, datetime

from application.ai_provider import (
    AiProviderError,
    AiProviderErrorKind,
    AiRequest,
    AiTask,
    ProviderDescriptor,
)
from domain.advisory_output import AdvisoryOutput, Provenance

MOCK_PROVIDER_ID = "deterministic-mock"
MOCK_MODEL_ID = "none"
MOCK_UNCERTAINTY_NOTE = "MOCK: this text is a fixed template, not model output. It carries no clinical meaning."


class DeterministicMockAiProvider:
    """Explicit demo mock (HC-151, D1). No model is called and no input text is echoed back."""

    def __init__(
        self,
        supported_tasks: frozenset[AiTask] = frozenset(AiTask),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._supported_tasks = supported_tasks
        self._clock = clock

    def describe(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=MOCK_PROVIDER_ID,
            model_id=MOCK_MODEL_ID,
            is_mock=True,
            supported_tasks=self._supported_tasks,
        )

    def generate(self, request: AiRequest) -> AdvisoryOutput:
        if not request.instructions.strip() or not request.input_text.strip():
            raise AiProviderError(
                AiProviderErrorKind.INVALID_REQUEST,
                "Instructions and input text are required.",
            )
        if request.task not in self._supported_tasks:
            raise AiProviderError(
                AiProviderErrorKind.UNSUPPORTED_TASK,
                f"Task '{request.task.value}' is not supported by {MOCK_PROVIDER_ID}.",
            )
        return AdvisoryOutput(
            text=(
                f"[MOCK] Deterministic {request.task.value} placeholder for request "
                f"{request.request_id} ({len(request.input_text)} input characters)."
            ),
            provenance=Provenance(
                provider_id=MOCK_PROVIDER_ID,
                model_id=MOCK_MODEL_ID,
                is_mock=True,
                generated_at=self._clock(),
            ),
            uncertainty_notes=(MOCK_UNCERTAINTY_NOTE,),
        )
