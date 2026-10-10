"""AiProvider adapter for Claude through the Claude Agent SDK (ADR-0006 primary provider).

The SDK drives the locally installed Claude Code CLI and uses its login, so this
service holds no API key. The agent is run as a plain text-in, JSON-out call:
no built-in tools, no user or project settings, and a structured-output schema
when the request provides one. Source text is sent to Anthropic.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKError,
    CLIConnectionError,
    ProcessError,
    ResultMessage,
    query,
)

from application.ai_provider import (
    AiProviderError,
    AiProviderErrorKind,
    AiRequest,
    AiTask,
    ProviderDescriptor,
)
from domain.advisory_output import AdvisoryOutput, Provenance

PROVIDER_ID = "claude-agent-sdk"

QueryFn = Callable[..., AsyncIterator[Any]]


class ClaudeAgentSdkProvider:
    def __init__(
        self,
        model: str = "claude-opus-5-5",
        timeout_seconds: float = 120.0,
        query_fn: QueryFn = query,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._query = query_fn
        self._clock = clock

    def describe(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=PROVIDER_ID,
            model_id=self._model,
            is_mock=False,
            supported_tasks=frozenset(AiTask),
        )

    def generate(self, request: AiRequest) -> AdvisoryOutput:
        if not request.instructions.strip() or not request.input_text.strip():
            raise AiProviderError(
                AiProviderErrorKind.INVALID_REQUEST,
                "Instructions and input text are required.",
            )
        options = ClaudeAgentOptions(
            model=self._model,
            system_prompt=request.instructions,
            tools=[],
            setting_sources=[],
            max_turns=3,
            output_format={"type": "json_schema", "schema": dict(request.output_schema)}
            if request.output_schema is not None
            else None,
        )
        try:
            result = asyncio.run(
                asyncio.wait_for(
                    self._final_result(request.input_text, options),
                    timeout=self._timeout_seconds,
                )
            )
        except TimeoutError as error:
            raise AiProviderError(
                AiProviderErrorKind.TIMEOUT, "Claude did not answer in time."
            ) from error
        except (CLIConnectionError, ProcessError, ClaudeSDKError) as error:
            raise AiProviderError(
                AiProviderErrorKind.UNAVAILABLE, f"Claude is unavailable: {error}"
            ) from error

        text = _result_text(result, structured=request.output_schema is not None)
        return AdvisoryOutput(
            text=text,
            provenance=Provenance(
                provider_id=PROVIDER_ID,
                model_id=self._model,
                is_mock=False,
                generated_at=self._clock(),
            ),
        )

    async def _final_result(self, prompt: str, options: ClaudeAgentOptions) -> Any:
        result = None
        async for message in self._query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result = message
        return result


def _result_text(result: Any, structured: bool) -> str:
    if result is None:
        raise AiProviderError(
            AiProviderErrorKind.UNAVAILABLE, "Claude returned no result."
        )
    if result.is_error or result.subtype != "success":
        raise AiProviderError(
            AiProviderErrorKind.UNAVAILABLE,
            f"Claude returned an error result ({result.subtype}).",
        )
    if structured and result.structured_output is not None:
        return json.dumps(result.structured_output)
    if isinstance(result.result, str) and result.result.strip():
        return result.result
    raise AiProviderError(AiProviderErrorKind.UNAVAILABLE, "Claude returned no text.")
