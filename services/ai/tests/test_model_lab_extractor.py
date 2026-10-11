import json

import pytest

from application.ai_provider import AiProviderErrorKind, AiTask
from application.extract_lab_results import (
    ExtractLabResults,
    LabExtractionRequest,
    LabExtractionUnavailable,
)
from application.model_lab_extractor import (
    INSTRUCTIONS,
    OUTPUT_SCHEMA,
    ModelLabExtractor,
)
from domain.lab_extraction import ExtractorKind, LabFlag, ReferenceRange
from tests.test_lab_extraction_domain import REPORT
from tests.test_model_clinical_extractor import FIXED_TIME, ScriptedProvider


def row(
    test="Potassium",
    value=5.6,
    unit="mmol/L",
    low=3.5,
    high=5.0,
    quote="Potassium : 5,6 mmol/L (3,5 – 5,0)",
):
    return {
        "test": test,
        "value": value,
        "unit": unit,
        "reference_low": low,
        "reference_high": high,
        "quote": quote,
    }


def extract(rows, **kwargs):
    provider = ScriptedProvider(text=json.dumps({"results": rows}), **kwargs)
    return ModelLabExtractor(provider, new_request_id=lambda: "req-1").extract(
        REPORT
    ), provider


def test_sends_the_report_with_the_schema_as_an_extraction():
    _, provider = extract([])

    [request] = provider.requests
    assert (request.task, request.input_text, request.output_schema) == (
        AiTask.EXTRACTION,
        REPORT,
        OUTPUT_SCHEMA,
    )


def test_the_model_is_never_asked_to_judge_abnormality():
    assert "judge whether a value is normal or abnormal" in INSTRUCTIONS
    assert "Never use a usual or typical range" in INSTRUCTIONS
    assert "flag" not in json.dumps(OUTPUT_SCHEMA)


def test_maps_rows_and_reports_the_provider():
    output, _ = extract([row(), row("CRP", 3, "mg/L", None, None, "CRP : 3 mg/L")])

    assert [p.reference_range for p in output.proposals] == [
        ReferenceRange(3.5, 5.0),
        None,
    ]
    assert (output.extractor.kind, output.extractor.name, output.malformed) == (
        ExtractorKind.MODEL,
        "claude-agent-sdk",
        0,
    )


def test_counts_malformed_rows():
    output, _ = extract(
        [
            "not an object",
            row(value="5,6"),
            row(value=True),
            {k: v for k, v in row().items() if k != "quote"},
            row(low=5.0, high=3.5),  # range inverted: kept without a range
            row(),
        ]
    )

    assert output.malformed == 4
    assert [p.reference_range for p in output.proposals] == [
        None,
        ReferenceRange(3.5, 5.0),
    ]


@pytest.mark.parametrize("text", ["not json", "[]", ""])
def test_unusable_model_output_is_unavailable(text):
    with pytest.raises(LabExtractionUnavailable):
        ModelLabExtractor(ScriptedProvider(text=text)).extract(REPORT)


def test_provider_failure_is_unavailable():
    with pytest.raises(LabExtractionUnavailable):
        ModelLabExtractor(ScriptedProvider(error=AiProviderErrorKind.TIMEOUT)).extract(
            REPORT
        )


def test_the_use_case_verifies_flags_and_counts():
    model = ModelLabExtractor(
        ScriptedProvider(
            text=json.dumps(
                {
                    "results": [
                        row(),
                        row(
                            "Sodium",
                            131,
                            "mmol/L",
                            135,
                            145,
                            "Sodium : 131 mmol/L (135 – 145)",
                        ),
                        row(
                            "Calcium",
                            2.4,
                            "mmol/L",
                            2.2,
                            2.6,
                            "Calcium : 2,4 mmol/L (2,2 – 2,6)",
                        ),
                        "malformed",
                    ]
                }
            )
        )
    )
    draft = ExtractLabResults(model, clock=lambda: FIXED_TIME, new_id=lambda: "x-1")(
        LabExtractionRequest("pat-a", "clin-x", REPORT)
    )

    assert [(r.result_id, r.test, r.flag) for r in draft.results] == [
        ("result-1", "Potassium", LabFlag.HIGH),
        ("result-2", "Sodium", LabFlag.LOW),
    ]
    # Calcium is not in the report; one row was malformed.
    assert draft.unverified_results_dropped == 2
    assert (draft.advisory, draft.review_status.value) == (
        True,
        "pending_clinician_review",
    )
