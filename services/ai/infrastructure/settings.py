"""Runtime configuration from environment variables. No secrets are read here (ADR-0006)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class ExtractionMode(StrEnum):
    MODEL = "model"  # real providers, Claude first, then Ollama
    FIXTURE = "fixture"  # deterministic demo fixtures (MOCKED), no model call


class ReviewMode(StrEnum):
    MODEL = "model"  # real providers, as for extraction
    FIXTURE = "fixture"  # deterministic demo rules (MOCKED), no model call


class LabMode(StrEnum):
    MODEL = "model"  # real providers, as for extraction
    FIXTURE = "fixture"  # fixed results for the demo report (MOCKED), no model call


class ExplanationMode(StrEnum):
    MODEL = "model"  # real providers, model text checked, template when it fails
    TEMPLATE = "template"  # deterministic template only, no model call


class ProviderName(StrEnum):
    CLAUDE = "claude"
    OLLAMA = "ollama"


@dataclass(frozen=True)
class Settings:
    extraction_mode: ExtractionMode = ExtractionMode.MODEL
    # HC-154: the hospital onboarding dossier review.
    review_mode: ReviewMode = ReviewMode.MODEL
    # HC-155: lab result extraction.
    lab_mode: LabMode = LabMode.MODEL
    # HC-156: medication warning explanation.
    explanation_mode: ExplanationMode = ExplanationMode.MODEL
    # HC-157: priority queue explanation, the same two modes.
    priority_explanation_mode: ExplanationMode = ExplanationMode.MODEL
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
        review_mode=ReviewMode(env.get("AI_REVIEW_MODE", defaults.review_mode)),
        lab_mode=LabMode(env.get("AI_LAB_MODE", defaults.lab_mode)),
        explanation_mode=ExplanationMode(
            env.get("AI_EXPLANATION_MODE", defaults.explanation_mode)
        ),
        priority_explanation_mode=ExplanationMode(
            env.get("AI_PRIORITY_EXPLANATION_MODE", defaults.priority_explanation_mode)
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
