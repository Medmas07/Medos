import pytest

from application.ai_provider import (
    AiProviderError,
    AiProviderErrorKind,
    AiRequest,
    AiTask,
    ProviderDescriptor,
)
from application.fallback_ai_provider import FallbackAiProvider
from domain.advisory_output import AdvisoryOutput, Provenance
from tests.test_ai_provider_contract import FIXED_TIME

REQUEST = AiRequest(
    request_id="r1", task=AiTask.EXTRACTION, instructions="x", input_text="y"
)


class StubProvider:
    def __init__(self, provider_id, error=None, tasks=frozenset(AiTask)):
        self.provider_id, self.error, self.tasks, self.calls = (
            provider_id,
            error,
            tasks,
            0,
        )

    def describe(self):
        return ProviderDescriptor(self.provider_id, "m", False, self.tasks)

    def generate(self, request):
        self.calls += 1
        if self.error:
            raise AiProviderError(self.error, f"{self.provider_id} failed")
        return AdvisoryOutput(
            text="ok", provenance=Provenance(self.provider_id, "m", False, FIXED_TIME)
        )


def test_uses_primary_when_it_answers():
    primary, fallback = StubProvider("claude"), StubProvider("ollama")

    output = FallbackAiProvider([primary, fallback]).generate(REQUEST)

    assert output.provenance.provider_id == "claude"
    assert fallback.calls == 0
    assert output.uncertainty_notes == ()


@pytest.mark.parametrize(
    "kind", [AiProviderErrorKind.UNAVAILABLE, AiProviderErrorKind.TIMEOUT]
)
def test_falls_back_when_primary_is_unavailable_or_slow(kind):
    output = FallbackAiProvider(
        [StubProvider("claude", error=kind), StubProvider("ollama")]
    ).generate(REQUEST)

    assert output.provenance.provider_id == "ollama"
    assert "claude" in output.uncertainty_notes[-1]


def test_does_not_fall_back_on_invalid_request():
    fallback = StubProvider("ollama")
    chain = FallbackAiProvider(
        [StubProvider("claude", error=AiProviderErrorKind.INVALID_REQUEST), fallback]
    )

    with pytest.raises(AiProviderError) as error:
        chain.generate(REQUEST)

    assert error.value.kind is AiProviderErrorKind.INVALID_REQUEST
    assert fallback.calls == 0


def test_reports_unavailable_when_every_provider_fails():
    chain = FallbackAiProvider(
        [
            StubProvider("claude", error=AiProviderErrorKind.UNAVAILABLE),
            StubProvider("ollama", error=AiProviderErrorKind.TIMEOUT),
        ]
    )

    with pytest.raises(AiProviderError) as error:
        chain.generate(REQUEST)

    assert error.value.kind is AiProviderErrorKind.UNAVAILABLE
    assert "claude" in str(error.value) and "ollama" in str(error.value)


def test_skips_providers_that_do_not_support_the_task():
    skipped = StubProvider("claude", tasks=frozenset({AiTask.SUMMARIZATION}))

    output = FallbackAiProvider([skipped, StubProvider("ollama")]).generate(REQUEST)

    assert output.provenance.provider_id == "ollama" and skipped.calls == 0


def test_describe_lists_the_chain_in_order():
    descriptor = FallbackAiProvider(
        [StubProvider("claude"), StubProvider("ollama")]
    ).describe()

    assert descriptor.provider_id == "claude > ollama"


def test_requires_a_provider():
    with pytest.raises(ValueError):
        FallbackAiProvider([])
