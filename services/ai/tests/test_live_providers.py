"""Opt-in live checks against real providers. Run with AI_LIVE_TESTS=1.

They send the fictional demo transcript to Claude (through the local Claude
Code login) and to the local Ollama server. They are skipped by default and in CI.
"""

import os

import pytest

from adapters.outbound.claude_agent_sdk_provider import ClaudeAgentSdkProvider
from adapters.outbound.fixture_extractor import DEMO_TRANSCRIPT
from adapters.outbound.ollama_provider import OllamaAiProvider
from application.model_clinical_extractor import ModelClinicalExtractor
from domain.clinical_extraction import ExtractionSource, ItemCategory, SourceType
from infrastructure.settings import load_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("AI_LIVE_TESTS") != "1", reason="live provider tests are opt-in"
)

SETTINGS = load_settings()
SOURCE = ExtractionSource(SourceType.TRANSCRIPT, DEMO_TRANSCRIPT)


@pytest.mark.parametrize(
    "provider",
    [
        ClaudeAgentSdkProvider(model=SETTINGS.claude_model, timeout_seconds=180),
        OllamaAiProvider(
            model=SETTINGS.ollama_model,
            base_url=SETTINGS.ollama_base_url,
            timeout_seconds=180,
        ),
    ],
    ids=["claude", "ollama"],
)
def test_live_extraction_of_demo_transcript(provider):
    output = ModelClinicalExtractor(provider).extract(SOURCE)

    assert output.info.mocked is False
    assert output.items, "expected at least one extracted item"
    assert ItemCategory.MEASUREMENT in {i.category for i in output.items}
    for extracted in output.items:
        assert (
            DEMO_TRANSCRIPT[extracted.evidence.start : extracted.evidence.end]
            == extracted.evidence.quote
        )
