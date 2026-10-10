from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from adapters.outbound.fixture_extractor import DEMO_TRANSCRIPT
from tests.conftest import fixture_client

CONTRACT = yaml.safe_load(
    (
        Path(__file__).resolve().parents[3]
        / "contracts/api/ai/clinical-extraction.v1.yaml"
    ).read_text()
)
client = fixture_client()


def validator(schema_name: str) -> Draft202012Validator:
    schema = {
        "$ref": f"#/components/schemas/{schema_name}",
        "components": CONTRACT["components"],
    }
    return Draft202012Validator(schema, format_checker=FormatChecker())


def post(body):
    return client.post("/v1/clinical-extractions", json=body)


DEMO_REQUEST = {
    "patient_ref": "patient-a",
    "encounter_ref": "encounter-a-001",
    "requested_by": "dr-x",
    "source": {"type": "transcript", "text": DEMO_TRANSCRIPT, "language": "en"},
}


def test_demo_request_conforms_to_contract():
    validator("ExtractionRequest").validate(DEMO_REQUEST)


def test_demo_transcript_returns_contract_conformant_draft():
    response = post(DEMO_REQUEST)

    assert response.status_code == 200
    body = response.json()
    validator("ExtractionDraft").validate(body)
    assert body["review_status"] == "pending_clinician_review"
    assert body["advisory"] is True
    assert body["provenance"]["mocked"] is True
    assert body["provenance"]["extractor"]["kind"] == "deterministic_fixture"
    assert len(body["items"]) == 7


def test_unknown_text_returns_empty_conformant_draft_without_encounter():
    response = post(
        {
            "patient_ref": "patient-a",
            "requested_by": "dr-x",
            "source": {"type": "physician_note", "text": "Routine follow-up."},
        }
    )

    assert response.status_code == 200
    body = response.json()
    validator("ExtractionDraft").validate(body)
    assert body["items"] == [] and "encounter_ref" not in body


@pytest.mark.parametrize(
    "change",
    [
        {"source": {"type": "transcript", "text": ""}},
        {"source": {"type": "audio", "text": "x"}},
        {"patient_ref": "Jane Doe"},
        {"unexpected": True},
    ],
)
def test_invalid_request_returns_contract_problem(change):
    response = post({**DEMO_REQUEST, **change})

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    validator("Problem").validate(response.json())
    assert response.json()["code"] == "invalid_request"


def test_whitespace_only_text_is_rejected_by_domain_rule():
    response = post({**DEMO_REQUEST, "source": {"type": "transcript", "text": "   "}})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
