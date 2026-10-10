from collections.abc import Sequence
from dataclasses import replace

from application.ai_provider import (
    AiProvider,
    AiProviderError,
    AiProviderErrorKind,
    AiRequest,
    ProviderDescriptor,
)
from domain.advisory_output import AdvisoryOutput

# Only failures of the provider itself justify trying the next one; a bad request fails everywhere.
FALLBACK_KINDS = frozenset(
    {AiProviderErrorKind.UNAVAILABLE, AiProviderErrorKind.TIMEOUT}
)


class FallbackAiProvider:
    """Tries providers in order and returns the first answer (ADR-0006)."""

    def __init__(self, providers: Sequence[AiProvider]):
        if not providers:
            raise ValueError("At least one provider is required.")
        self._providers = tuple(providers)

    def describe(self) -> ProviderDescriptor:
        descriptors = [provider.describe() for provider in self._providers]
        return ProviderDescriptor(
            provider_id=" > ".join(d.provider_id for d in descriptors),
            model_id=" > ".join(d.model_id for d in descriptors),
            is_mock=any(d.is_mock for d in descriptors),
            supported_tasks=frozenset().union(
                *(d.supported_tasks for d in descriptors)
            ),
        )

    def generate(self, request: AiRequest) -> AdvisoryOutput:
        failures: list[str] = []
        for provider in self._providers:
            descriptor = provider.describe()
            if request.task not in descriptor.supported_tasks:
                continue
            try:
                output = provider.generate(request)
            except AiProviderError as error:
                if error.kind not in FALLBACK_KINDS:
                    raise
                failures.append(f"{descriptor.provider_id}: {error.kind.value}")
                continue
            if failures:
                note = (
                    "Answered by fallback provider after: " + "; ".join(failures) + "."
                )
                output = replace(
                    output, uncertainty_notes=(*output.uncertainty_notes, note)
                )
            return output
        if not failures:
            raise AiProviderError(
                AiProviderErrorKind.UNSUPPORTED_TASK,
                f"No provider supports task '{request.task.value}'.",
            )
        raise AiProviderError(
            AiProviderErrorKind.UNAVAILABLE,
            "No AI provider could answer: " + "; ".join(failures) + ".",
        )
