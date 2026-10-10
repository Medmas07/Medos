import json

import httpx
import pytest

from adapters.outbound.ollama_provider import OllamaAiProvider
from application.ai_provider import (
    AiProviderError,
    AiProviderErrorKind,
    AiRequest,
    AiTask,
)
from tests.test_ai_provider_contract import FIXED_TIME

REQUEST = AiRequest(
    request_id="r1",
    task=AiTask.EXTRACTION,
    instructions="Extract.",
    input_text="Fictional note.",
    output_schema={"type": "object"},
)


def provider(handler) -> OllamaAiProvider:
    client = httpx.Client(
        base_url="http://ollama.test", transport=httpx.MockTransport(handler)
    )
    return OllamaAiProvider(model="qwen2.5:3b", client=client, clock=lambda: FIXED_TIME)


def test_sends_chat_request_with_schema_and_returns_content():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": '{"a": 1}'}}
        )

    output = provider(handler).generate(REQUEST)

    assert seen["path"] == "/api/chat"
    assert seen["body"]["model"] == "qwen2.5:3b"
    assert seen["body"]["format"] == {"type": "object"}
    assert seen["body"]["stream"] is False
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]
    assert output.text == '{"a": 1}'
    assert output.provenance.provider_id == "ollama"


@pytest.mark.parametrize(
    "handler, kind",
    [
        (
            lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused")),
            AiProviderErrorKind.UNAVAILABLE,
        ),
        (
            lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow")),
            AiProviderErrorKind.TIMEOUT,
        ),
        (
            lambda r: httpx.Response(404, json={"error": "model not found"}),
            AiProviderErrorKind.UNAVAILABLE,
        ),
        (
            lambda r: httpx.Response(200, json={"unexpected": True}),
            AiProviderErrorKind.UNAVAILABLE,
        ),
        (
            lambda r: httpx.Response(200, json={"message": {"content": "  "}}),
            AiProviderErrorKind.UNAVAILABLE,
        ),
    ],
    ids=[
        "connection_refused",
        "timeout",
        "model_missing",
        "unexpected_body",
        "empty_text",
    ],
)
def test_maps_failures_to_provider_errors(handler, kind):
    with pytest.raises(AiProviderError) as error:
        provider(handler).generate(REQUEST)

    assert error.value.kind is kind
