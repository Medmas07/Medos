import pytest

from infrastructure.settings import (
    ExplanationMode,
    ExtractionMode,
    LabMode,
    ProviderName,
    ReviewMode,
    Settings,
    load_settings,
)


def test_defaults_to_claude_then_ollama():
    settings = load_settings({})

    assert settings == Settings()
    assert settings.extraction_mode is ExtractionMode.MODEL
    assert settings.providers == (ProviderName.CLAUDE, ProviderName.OLLAMA)
    assert settings.claude_model == "claude-opus-5-5"


def test_reads_overrides_from_the_environment():
    settings = load_settings(
        {
            "AI_EXTRACTION_MODE": "fixture",
            "AI_PROVIDERS": "ollama",
            "OLLAMA_MODEL": "llama3.2:3b",
            "AI_PROVIDER_TIMEOUT_SECONDS": "30",
        }
    )

    assert settings.extraction_mode is ExtractionMode.FIXTURE
    assert settings.providers == (ProviderName.OLLAMA,)
    assert settings.ollama_model == "llama3.2:3b"
    assert settings.provider_timeout_seconds == 30.0


def test_rejects_unknown_provider():
    with pytest.raises(ValueError):
        load_settings({"AI_PROVIDERS": "claude,gpt"})


def test_the_review_mode_is_model_by_default_and_set_on_its_own():
    assert load_settings({}).review_mode is ReviewMode.MODEL

    settings = load_settings({"AI_REVIEW_MODE": "fixture"})
    assert (settings.review_mode, settings.extraction_mode) == (
        ReviewMode.FIXTURE,
        ExtractionMode.MODEL,
    )
    with pytest.raises(ValueError):
        load_settings({"AI_REVIEW_MODE": "simulated"})


def test_the_lab_mode_is_model_by_default_and_set_on_its_own():
    assert load_settings({}).lab_mode is LabMode.MODEL
    assert load_settings({"AI_LAB_MODE": "fixture"}).lab_mode is LabMode.FIXTURE
    with pytest.raises(ValueError):
        load_settings({"AI_LAB_MODE": "simulated"})


def test_the_explanation_mode_is_model_by_default_and_set_on_its_own():
    assert load_settings({}).explanation_mode is ExplanationMode.MODEL
    assert (
        load_settings({"AI_EXPLANATION_MODE": "template"}).explanation_mode
        is ExplanationMode.TEMPLATE
    )
    with pytest.raises(ValueError):
        load_settings({"AI_EXPLANATION_MODE": "fixture"})


def test_the_priority_explanation_mode_is_model_by_default_and_set_on_its_own():
    assert load_settings({}).priority_explanation_mode is ExplanationMode.MODEL
    settings = load_settings({"AI_PRIORITY_EXPLANATION_MODE": "template"})
    assert settings.priority_explanation_mode is ExplanationMode.TEMPLATE
    assert settings.explanation_mode is ExplanationMode.MODEL
    with pytest.raises(ValueError):
        load_settings({"AI_PRIORITY_EXPLANATION_MODE": "fixture"})
