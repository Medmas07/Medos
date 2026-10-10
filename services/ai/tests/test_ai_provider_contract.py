from datetime import UTC, datetime

import pytest

from adapters.outbound.mock_ai_provider import DeterministicMockAiProvider
from application.ai_provider import (
    AiProvider,
    AiProviderError,
    AiProviderErrorKind,
    AiRequest,
    AiTask,
)
from domain.advisory_output import ReviewState

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _real_adapters_with_test_doubles() -> list:
    """Claude and Ollama adapters wired to test doubles, so no model is called."""
    import httpx
    from claude_agent_sdk import ResultMessage

    from adapters.outbound.claude_agent_sdk_provider import ClaudeAgentSdkProvider
    from adapters.outbound.ollama_provider import OllamaAiProvider

    async def claude_query(*, prompt, options):
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="s1",
            result="Fictional summary.",
        )

    ollama = httpx.Client(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"message": {"content": "Fictional summary."}}
            )
        ),
    )
    return [
        ClaudeAgentSdkProvider(query_fn=claude_query, clock=lambda: FIXED_TIME),
        OllamaAiProvider(model="qwen2.5:3b", client=ollama, clock=lambda: FIXED_TIME),
    ]


# Every AiProvider adapter must pass these tests. Add future adapters here with a test double transport.
PROVIDERS = [
    DeterministicMockAiProvider(clock=lambda: FIXED_TIME),
    *_real_adapters_with_test_doubles(),
]


def _request(
    task: AiTask = AiTask.SUMMARIZATION, input_text: str = "Fictional note."
) -> AiRequest:
    return AiRequest(
        request_id="req-001",
        task=task,
        instructions="Summarize the note.",
        input_text=input_text,
    )


@pytest.mark.parametrize("provider", PROVIDERS)
def test_output_is_pending_human_review(provider: AiProvider):
    assert (
        provider.generate(_request()).review_state is ReviewState.PENDING_HUMAN_REVIEW
    )


@pytest.mark.parametrize("provider", PROVIDERS)
def test_output_provenance_matches_descriptor(provider: AiProvider):
    descriptor = provider.describe()
    provenance = provider.generate(_request()).provenance

    assert provenance.provider_id == descriptor.provider_id
    assert provenance.model_id == descriptor.model_id
    assert provenance.is_mock == descriptor.is_mock


@pytest.mark.parametrize("provider", PROVIDERS)
def test_blank_input_is_an_invalid_request(provider: AiProvider):
    with pytest.raises(AiProviderError) as error:
        provider.generate(_request(input_text="   "))

    assert error.value.kind is AiProviderErrorKind.INVALID_REQUEST


def test_mock_is_deterministic_and_labelled():
    provider = DeterministicMockAiProvider(clock=lambda: FIXED_TIME)

    first = provider.generate(_request())

    assert first == provider.generate(_request())
    assert first.text.startswith("[MOCK]")
    assert first.provenance.is_mock
    assert first.provenance.generated_at == FIXED_TIME
    assert first.uncertainty_notes


def test_mock_does_not_echo_input_text():
    output = DeterministicMockAiProvider().generate(
        _request(input_text="Fictional marker XYZ")
    )

    assert "XYZ" not in output.text


def test_mock_rejects_unsupported_task():
    provider = DeterministicMockAiProvider(
        supported_tasks=frozenset({AiTask.EXPLANATION})
    )

    with pytest.raises(AiProviderError) as error:
        provider.generate(_request(task=AiTask.EXTRACTION))

    assert error.value.kind is AiProviderErrorKind.UNSUPPORTED_TASK
