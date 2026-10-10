"""Runtime configuration from environment variables. No secrets are read here (ADR-0006)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class ExtractionMode(StrEnum):
    MODEL = "model"  # real providers, Claude first, then Ollama
    FIXTURE = "fixture"  # deterministic demo fixtures (MOCKED), no model call


class ProviderName(StrEnum):
    CLAUDE = "claude"
    OLLAMA = "ollama"


@dataclass(frozen=True)
class Settings:
    extraction_mode: ExtractionMode = ExtractionMode.MODEL
    providers: tuple[ProviderName, ...] = (ProviderName.CLAUDE, ProviderName.OLLAMA)
    claude_model: str = "claude-opus-5-5"
    ollama_model: str = "qwen2.5:3b"
    ollama_base_url: str = "http://localhost:11434"
    provider_timeout_seconds: float = 120.0


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    defaults = Settings()
    providers = env.get("AI_PROVIDERS")
    return Settings(
        extraction_mode=ExtractionMode(
            env.get("AI_EXTRACTION_MODE", defaults.extraction_mode)
        ),
        providers=tuple(
            ProviderName(p.strip()) for p in providers.split(",") if p.strip()
        )
        if providers
        else defaults.providers,
        claude_model=env.get("CLAUDE_MODEL", defaults.claude_model),
        ollama_model=env.get("OLLAMA_MODEL", defaults.ollama_model),
        ollama_base_url=env.get("OLLAMA_BASE_URL", defaults.ollama_base_url),
        provider_timeout_seconds=float(
            env.get("AI_PROVIDER_TIMEOUT_SECONDS", defaults.provider_timeout_seconds)
        ),
    )
