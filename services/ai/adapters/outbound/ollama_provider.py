"""AiProvider adapter for a local Ollama server (ADR-0006 fallback provider).

The model runs on the same machine, so source text does not leave it.
"""

from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from application.ai_provider import (
    AiProviderError,
    AiProviderErrorKind,
    AiRequest,
    AiTask,
    ProviderDescriptor,
)
from domain.advisory_output import AdvisoryOutput, Provenance

PROVIDER_ID = "ollama"


class OllamaAiProvider:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 120.0,
        client: httpx.Client | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._model = model
        self._client = client or httpx.Client(
            base_url=base_url, timeout=timeout_seconds
        )
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
        body = {
            "model": self._model,
            "stream": False,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": request.input_text},
            ],
        }
        if request.output_schema is not None:
            body["format"] = dict(request.output_schema)
        try:
            response = self._client.post("/api/chat", json=body)
        except httpx.TimeoutException as error:
            raise AiProviderError(
                AiProviderErrorKind.TIMEOUT, "Ollama did not answer in time."
            ) from error
        except httpx.HTTPError as error:
            raise AiProviderError(
                AiProviderErrorKind.UNAVAILABLE, f"Ollama is not reachable: {error}"
            ) from error
        if response.status_code != 200:
            raise AiProviderError(
                AiProviderErrorKind.UNAVAILABLE,
                f"Ollama returned HTTP {response.status_code}: {response.text[:200]}",
            )
        try:
            text = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as error:
            raise AiProviderError(
                AiProviderErrorKind.UNAVAILABLE,
                "Ollama returned an unexpected response.",
            ) from error
        if not isinstance(text, str) or not text.strip():
            raise AiProviderError(
                AiProviderErrorKind.UNAVAILABLE, "Ollama returned no text."
            )
        return AdvisoryOutput(
            text=text,
            provenance=Provenance(
                provider_id=PROVIDER_ID,
                model_id=self._model,
                is_mock=False,
                generated_at=self._clock(),
            ),
        )
