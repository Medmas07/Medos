"""Hospital document review over HTTP against contracts/api/ai/hospital-document-review.v1.yaml.

Fixture mode, and model mode with test-double providers only: no model is called.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from adapters.inbound.http.hospital_document_review import create_router
from application.ai_provider import AiProviderErrorKind
from application.fallback_ai_provider import FallbackAiProvider
from application.model_document_reviewer import ModelDocumentReviewer
from application.review_hospital_documents import ReviewHospitalDocuments
from tests.conftest import fixture_client
from tests.test_fallback_ai_provider import StubProvider
from tests.test_model_clinical_extractor import ScriptedProvider

CONTRACT = yaml.safe_load(
    (
        Path(__file__).resolve().parents[3]
        / "contracts/api/ai/hospital-document-review.v1.yaml"
    ).read_text(encoding="utf-8")
)
OPERATION = CONTRACT["paths"]["/v1/hospital-document-reviews"]["post"]
HOSPITAL_C = OPERATION["requestBody"]["content"]["application/json"]["examples"][
    "hospitalC"
]["value"]
EXAMPLES = OPERATION["responses"]["200"]["content"]["application/json"]["examples"]
PATH = "/v1/hospital-document-reviews"


def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": CONTRACT["components"]},
        format_checker=FormatChecker(),
    )


def valid(body: dict, name: str = "DocumentReview") -> dict:
    errors = list(validator(name).iter_errors(body))
    assert not errors, errors[0].message
    return body


def without_volatile(body: dict) -> dict:
    body = json.loads(json.dumps(body))
    body.pop("review_id")
    body["provenance"].pop("generated_at")
    return body


def model_client(provider) -> TestClient:
    app = FastAPI()
    app.include_router(
        create_router(
            ReviewHospitalDocuments(
                ModelDocumentReviewer(provider), clock=lambda: datetime.now(UTC)
            )
        )
    )
    return TestClient(app)


def test_the_request_example_matches_the_contract():
    valid(HOSPITAL_C, "ReviewRequest")


def test_fixture_review_of_hospital_c_is_the_contract_example():
    response = fixture_client().post(PATH, json=HOSPITAL_C)

    assert response.status_code == 200
    body = valid(response.json())
    assert without_volatile(body) == without_volatile(
        EXAMPLES["fixtureHospitalC"]["value"]
    )


def test_model_review_keeps_cited_findings_and_drops_invented_ones():
    payload = {
        "findings": [
            {
                "category": "inconsistency",
                "message": "Le questionnaire déclare PostgreSQL 13, mais le document d'architecture indique PostgreSQL 12.",
                "field_paths": ["technical_questionnaire.database"],
                "evidence": {
                    "document_ref": "doc-c-architecture",
                    "quote": "Sa base de données est PostgreSQL 12",
                },
            },
            {
                "category": "missing_information",
                "message": "Aucun contact de sécurité n'est renseigné.",
                "field_paths": ["administrative_profile.security_contact"],
                "evidence": None,
            },
            {
                "category": "inconsistency",
                "message": "Le nombre de lits ne correspond pas au registre.",
                "field_paths": ["administrative_profile.national_registry_beds"],
                "evidence": None,
            },
        ]
    }

    body = valid(
        model_client(ScriptedProvider(text=json.dumps(payload)))
        .post(PATH, json=HOSPITAL_C)
        .json()
    )

    assert without_volatile(body) == without_volatile(
        EXAMPLES["modelHospitalC"]["value"]
    )
    assert body["provenance"]["mocked"] is False


def test_every_provider_failing_is_a_503():
    chain = FallbackAiProvider(
        [
            StubProvider("claude-agent-sdk", AiProviderErrorKind.UNAVAILABLE),
            StubProvider("ollama", AiProviderErrorKind.UNAVAILABLE),
        ]
    )

    response = model_client(chain).post(PATH, json=HOSPITAL_C)

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert valid(response.json(), "Problem")["code"] == "review_unavailable"


def changed(**changes):
    return {**HOSPITAL_C, **changes}


@pytest.mark.parametrize(
    "body",
    [
        changed(fields=[]),
        changed(fields=[{"path": "Administrative.Profile", "value": "x"}]),
        changed(fields=[{"path": "a", "value": {"nested": True}}]),
        changed(fields=[{"path": "a", "value": 1}, {"path": "a", "value": 2}]),
        changed(application_ref="app hospital c"),
        changed(diagnosis="none"),
        {k: v for k, v in HOSPITAL_C.items() if k != "requested_by"},
        changed(
            documents=[
                {
                    "document_ref": "doc-1",
                    "type": "t",
                    "title": "t",
                    "status": "received",
                    "text": "",
                }
            ]
        ),
    ],
)
def test_an_invalid_request_is_a_400(body):
    response = fixture_client().post(PATH, json=body)

    assert response.status_code == 400
    assert valid(response.json(), "Problem")["code"] == "invalid_request"


def test_malformed_json_is_a_400():
    response = fixture_client().post(
        PATH, content="{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 400


def test_the_extraction_route_keeps_its_own_validation_answers():
    response = fixture_client().post("/v1/clinical-extractions", json={})

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid clinical extraction request"


class EventLoopProvider(ScriptedProvider):
    """Like the Claude Agent SDK adapter: generate() runs its own event loop."""

    def generate(self, request):
        async def answer():
            return super(EventLoopProvider, self).generate(request)

        return asyncio.run(answer())


def test_a_provider_running_its_own_event_loop_works_through_the_route():
    response = model_client(EventLoopProvider(text=json.dumps({"findings": []}))).post(
        PATH, json=HOSPITAL_C
    )

    assert response.status_code == 200, response.text
