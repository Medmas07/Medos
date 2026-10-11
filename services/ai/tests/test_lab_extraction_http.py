"""Lab extraction over HTTP against contracts/api/ai/lab-extraction.v1.yaml.

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

from adapters.inbound.http.lab_extraction import create_router
from adapters.outbound.fixture_lab_extractor import FixtureLabExtractor
from application.ai_provider import AiProviderErrorKind
from application.extract_lab_results import ExtractLabResults, LabExtractor
from application.fallback_ai_provider import FallbackAiProvider
from application.model_lab_extractor import ModelLabExtractor
from tests.conftest import fixture_client
from tests.test_fallback_ai_provider import StubProvider
from tests.test_model_clinical_extractor import ScriptedProvider

CONTRACT = yaml.safe_load(
    (
        Path(__file__).resolve().parents[3] / "contracts/api/ai/lab-extraction.v1.yaml"
    ).read_text(encoding="utf-8")
)
OPERATION = CONTRACT["paths"]["/v1/lab-extractions"]["post"]
DEMO = OPERATION["requestBody"]["content"]["application/json"]["examples"][
    "hospitalBPanel"
]["value"]
EXAMPLES = OPERATION["responses"]["200"]["content"]["application/json"]["examples"]
PATH = "/v1/lab-extractions"


def valid(body: dict, name: str = "LabExtractionDraft") -> dict:
    validator = Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": CONTRACT["components"]},
        format_checker=FormatChecker(),
    )
    errors = list(validator.iter_errors(body))
    assert not errors, errors[0].message
    return body


def without_volatile(body: dict) -> dict:
    body = json.loads(json.dumps(body))
    body.pop("extraction_id")
    body["provenance"].pop("generated_at")
    return body


def client_for(extractor: LabExtractor) -> TestClient:
    app = FastAPI()
    app.include_router(
        create_router(ExtractLabResults(extractor, clock=lambda: datetime.now(UTC)))
    )
    return TestClient(app)


def test_the_request_example_matches_the_contract():
    valid(DEMO, "LabExtractionRequest")


def test_fixture_extraction_of_the_demo_report_is_the_contract_example():
    response = fixture_client().post(PATH, json=DEMO)

    assert response.status_code == 200
    assert without_volatile(valid(response.json())) == without_volatile(
        EXAMPLES["fixtureHospitalB"]["value"]
    )


def test_the_fixture_knows_only_the_demo_report():
    body = valid(
        client_for(FixtureLabExtractor())
        .post(PATH, json={**DEMO, "source": {"text": "Autre compte rendu fictif."}})
        .json()
    )

    assert body["results"] == []


def test_a_model_extraction_conforms_and_its_flags_are_computed():
    rows = [
        {
            "test": "Hémoglobine",
            "value": 12.6,
            "unit": "g/dL",
            "reference_low": 12.0,
            "reference_high": 16.0,
            "quote": "Hémoglobine : 12,6 g/dL (12,0 – 16,0)",
        },
        {
            "test": "Plaquettes",
            "value": 245,
            "unit": "G/L",
            "reference_low": 150,
            "reference_high": 400,
            "quote": "Plaquettes : 245 G/L (150 – 400)",
        },
        {
            "test": "Créatinine",
            "value": 11.4,
            "unit": "mg/L",
            "reference_low": 6.0,
            "reference_high": 12.0,
            "quote": "Créatinine : 11,4 mg/L (6,0 – 12,0)",
        },
    ]
    provider = ScriptedProvider(text=json.dumps({"results": rows}))

    body = valid(client_for(ModelLabExtractor(provider)).post(PATH, json=DEMO).json())

    assert without_volatile(body) == without_volatile(
        EXAMPLES["modelHospitalB"]["value"]
    )


def test_every_provider_failing_is_a_503():
    chain = FallbackAiProvider(
        [
            StubProvider("claude-agent-sdk", AiProviderErrorKind.UNAVAILABLE),
            StubProvider("ollama", AiProviderErrorKind.UNAVAILABLE),
        ]
    )

    response = client_for(ModelLabExtractor(chain)).post(PATH, json=DEMO)

    assert response.status_code == 503
    assert valid(response.json(), "Problem")["code"] == "extraction_unavailable"


@pytest.mark.parametrize(
    "body",
    [
        {**DEMO, "source": {"text": ""}},
        {**DEMO, "source": {"text": "x" * 20_001}},
        {**DEMO, "patient_ref": "Leila Ben Ali"},
        {**DEMO, "flag": "high"},
        {k: v for k, v in DEMO.items() if k != "requested_by"},
    ],
)
def test_an_invalid_request_is_a_400(body):
    response = fixture_client().post(PATH, json=body)

    assert response.status_code == 400
    assert valid(response.json(), "Problem")["code"] == "invalid_request"


class EventLoopProvider(ScriptedProvider):
    """Like the Claude Agent SDK adapter: generate() runs its own event loop."""

    def generate(self, request):
        async def answer():
            return super(EventLoopProvider, self).generate(request)

        return asyncio.run(answer())


def test_a_provider_running_its_own_event_loop_works_through_the_route():
    response = client_for(
        ModelLabExtractor(EventLoopProvider(text=json.dumps({"results": []})))
    ).post(PATH, json=DEMO)

    assert response.status_code == 200, response.text
