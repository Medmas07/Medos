import json

import pytest

from adapters.outbound.fixture_extractor import DEMO_TRANSCRIPT
from application.ai_provider import AiProviderError, AiProviderErrorKind, AiTask
from application.extract_clinical_information import ExtractionUnavailable
from application.model_clinical_extractor import OUTPUT_SCHEMA, ModelClinicalExtractor
from domain.advisory_output import AdvisoryOutput, Provenance
from domain.clinical_extraction import (
    ExtractionSource,
    ExtractorKind,
    ItemCategory,
    SourceType,
)
from tests.test_ai_provider_contract import FIXED_TIME

SOURCE = ExtractionSource(SourceType.TRANSCRIPT, DEMO_TRANSCRIPT)


class ScriptedProvider:
    """Test double: returns fixed text, or raises, and records the request."""

    def __init__(self, text="", error=None, provider_id="claude-agent-sdk"):
        self.text, self.error, self.provider_id, self.requests = (
            text,
            error,
            provider_id,
            [],
        )

    def describe(self):  # pragma: no cover - not used by the extractor
        raise NotImplementedError

    def generate(self, request):
        self.requests.append(request)
        if self.error:
            raise AiProviderError(self.error, "provider failed")
        return AdvisoryOutput(
            text=self.text,
            provenance=Provenance(
                self.provider_id, "claude-opus-5-5", False, FIXED_TIME
            ),
        )


def item(category, text, quote, value=None, unit=None, abnormal=None):
    return {
        "category": category,
        "text": text,
        "evidence_quote": quote,
        "value": value,
        "unit": unit,
        "abnormal": abnormal,
    }


def run(payload, **kwargs):
    provider = ScriptedProvider(text=json.dumps(payload), **kwargs)
    return ModelClinicalExtractor(provider).extract(SOURCE), provider


def test_sends_an_extraction_request_with_the_schema():
    _, provider = run({"items": [], "missing_information": []})

    request = provider.requests[0]
    assert request.task is AiTask.EXTRACTION
    assert request.input_text == DEMO_TRANSCRIPT
    assert request.output_schema == OUTPUT_SCHEMA


def test_maps_items_with_evidence_located_in_the_source():
    output, _ = run(
        {
            "items": [
                item("symptom", "Mild nausea", "mild nausea"),
                item(
                    "measurement",
                    "Temperature 38.2 °C",
                    "Temperature is 38.2 °C",
                    38.2,
                    "°C",
                    True,
                ),
            ],
            "missing_information": [
                {"topic": "allergies", "prompt": "Allergies not mentioned."}
            ],
        }
    )

    nausea, temperature = output.items
    assert nausea.category is ItemCategory.SYMPTOM
    assert DEMO_TRANSCRIPT[nausea.evidence.start : nausea.evidence.end] == "mild nausea"
    assert (temperature.value, temperature.unit, temperature.abnormal) == (
        38.2,
        "°C",
        True,
    )
    assert [i.item_id for i in output.items] == ["item-1", "item-2"]
    assert all(i.confidence is None for i in output.items)
    assert output.missing_information[0].topic == "allergies"


def test_drops_items_whose_quote_is_not_in_the_source():
    output, _ = run(
        {
            "items": [
                item("symptom", "Chest pain", "severe chest pain"),
                item("symptom", "Mild nausea", "mild nausea"),
            ],
            "missing_information": [],
        }
    )

    assert [i.text for i in output.items] == ["Mild nausea"]
    assert output.items[0].item_id == "item-1"


def test_accepts_case_only_quote_differences_but_keeps_source_characters():
    output, _ = run(
        {"items": [item("symptom", "Nausea", "MILD NAUSEA")], "missing_information": []}
    )

    assert output.items[0].evidence.quote == "mild nausea"


def test_ignores_malformed_items_and_fields():
    output, _ = run(
        {
            "items": [
                item("prescription", "Not a category", "mild nausea"),
                {"category": "symptom"},
                item(
                    "measurement",
                    "Odd value",
                    "Temperature is 38.2 °C",
                    value=True,
                    unit="",
                ),
                "not an object",
            ],
            "missing_information": [{"topic": "", "prompt": "x"}, "bad"],
        }
    )

    assert len(output.items) == 1
    assert output.items[0].value is None and output.items[0].unit is None
    assert output.missing_information == ()


def test_reports_the_answering_provider_as_provenance():
    output, _ = run({"items": [], "missing_information": []}, provider_id="ollama")

    assert output.info.kind is ExtractorKind.MODEL
    assert (output.info.name, output.info.version, output.info.mocked) == (
        "ollama",
        "claude-opus-5-5",
        False,
    )


def test_strips_a_markdown_code_fence():
    provider = ScriptedProvider(
        text='```json\n{"items": [], "missing_information": []}\n```'
    )

    assert ModelClinicalExtractor(provider).extract(SOURCE).items == ()


@pytest.mark.parametrize("text", ["not json", "[1, 2]"])
def test_unusable_model_output_is_unavailable(text):
    with pytest.raises(ExtractionUnavailable):
        ModelClinicalExtractor(ScriptedProvider(text=text)).extract(SOURCE)


def test_provider_failure_is_unavailable():
    provider = ScriptedProvider(error=AiProviderErrorKind.UNAVAILABLE)

    with pytest.raises(ExtractionUnavailable):
        ModelClinicalExtractor(provider).extract(SOURCE)
