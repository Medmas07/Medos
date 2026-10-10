import asyncio
import json

import pytest
from claude_agent_sdk import CLINotFoundError, ProcessError, ResultMessage

from adapters.outbound.claude_agent_sdk_provider import ClaudeAgentSdkProvider
from application.ai_provider import (
    AiProviderError,
    AiProviderErrorKind,
    AiRequest,
    AiTask,
)
from tests.test_ai_provider_contract import FIXED_TIME

SCHEMA = {"type": "object"}
REQUEST = AiRequest(
    request_id="r1",
    task=AiTask.EXTRACTION,
    instructions="Extract.",
    input_text="Fictional note.",
    output_schema=SCHEMA,
)


def result(subtype="success", is_error=False, result_text=None, structured=None):
    return ResultMessage(
        subtype=subtype,
        duration_ms=1,
        duration_api_ms=1,
        is_error=is_error,
        num_turns=1,
        session_id="s1",
        result=result_text,
        structured_output=structured,
    )


def fake_query(*messages, error=None, delay=0.0, seen=None):
    async def query(*, prompt, options):
        if seen is not None:
            seen.update(prompt=prompt, options=options)
        if delay:
            await asyncio.sleep(delay)
        if error:
            raise error
        for message in messages:
            yield message

    return query


def provider(query_fn, timeout=5.0):
    return ClaudeAgentSdkProvider(
        timeout_seconds=timeout, query_fn=query_fn, clock=lambda: FIXED_TIME
    )


def test_runs_without_tools_or_settings_and_with_the_schema():
    seen = {}

    provider(fake_query(result(structured={"items": []}), seen=seen)).generate(REQUEST)

    options = seen["options"]
    assert seen["prompt"] == "Fictional note."
    assert options.system_prompt == "Extract."
    assert options.tools == [] and options.setting_sources == []
    assert options.model == "claude-opus-5-5"
    assert options.output_format == {"type": "json_schema", "schema": SCHEMA}


def test_returns_structured_output_as_json():
    output = provider(fake_query(result(structured={"items": [1]}))).generate(REQUEST)

    assert json.loads(output.text) == {"items": [1]}
    assert output.provenance.provider_id == "claude-agent-sdk"
    assert output.provenance.is_mock is False


def test_returns_result_text_without_a_schema():
    plain = AiRequest(
        request_id="r2", task=AiTask.SUMMARIZATION, instructions="x", input_text="y"
    )

    output = provider(fake_query(result(result_text="A summary."))).generate(plain)

    assert output.text == "A summary."


@pytest.mark.parametrize(
    "query_fn, kind",
    [
        (fake_query(error=CLINotFoundError()), AiProviderErrorKind.UNAVAILABLE),
        (
            fake_query(error=ProcessError("exit", exit_code=1)),
            AiProviderErrorKind.UNAVAILABLE,
        ),
        (
            fake_query(result(subtype="error_max_turns")),
            AiProviderErrorKind.UNAVAILABLE,
        ),
        (fake_query(result(is_error=True)), AiProviderErrorKind.UNAVAILABLE),
        (fake_query(), AiProviderErrorKind.UNAVAILABLE),
        (fake_query(result()), AiProviderErrorKind.UNAVAILABLE),
    ],
    ids=[
        "cli_missing",
        "process_error",
        "error_subtype",
        "is_error",
        "no_result",
        "empty_result",
    ],
)
def test_maps_failures_to_provider_errors(query_fn, kind):
    with pytest.raises(AiProviderError) as error:
        provider(query_fn).generate(REQUEST)

    assert error.value.kind is kind


def test_times_out():
    with pytest.raises(AiProviderError) as error:
        provider(fake_query(result(structured={}), delay=1.0), timeout=0.05).generate(
            REQUEST
        )

    assert error.value.kind is AiProviderErrorKind.TIMEOUT
