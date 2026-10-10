"""Model-mode HTTP behaviour against the contract, with test-double providers only."""

import json
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapters.inbound.http.clinical_extraction import (
    create_router,
    register_problem_handler,
)
from adapters.outbound.fixture_extractor import DEMO_TRANSCRIPT
from application.ai_provider import AiProviderErrorKind
from application.extract_clinical_information import ExtractClinicalInformation
from application.fallback_ai_provider import FallbackAiProvider
from application.model_clinical_extractor import ModelClinicalExtractor
from tests.test_clinical_extraction_http import validator
from tests.test_fallback_ai_provider import StubProvider
from tests.test_model_clinical_extractor import ScriptedProvider, item

REQUEST = {
    "patient_ref": "patient-a",
    "requested_by": "dr-x",
    "source": {"type": "transcript", "text": DEMO_TRANSCRIPT},
}


def client_for(provider) -> TestClient:
    app = FastAPI()
    app.include_router(
        create_router(
            ExtractClinicalInformation(
                ModelClinicalExtractor(provider), clock=lambda: datetime.now(UTC)
            )
        )
    )
    register_problem_handler(app)
    return TestClient(app)


def test_model_draft_conforms_to_contract_and_is_not_mocked():
    payload = {
        "items": [item("symptom", "Mild nausea", "mild nausea")],
        "missing_information": [],
    }
    response = client_for(ScriptedProvider(text=json.dumps(payload))).post(
        "/v1/clinical-extractions", json=REQUEST
    )

    assert response.status_code == 200
    body = response.json()
    validator("ExtractionDraft").validate(body)
    assert body["provenance"]["extractor"]["kind"] == "model"
    assert body["provenance"]["mocked"] is False
    assert body["review_status"] == "pending_clinician_review"


def test_all_providers_failing_returns_contract_503():
    chain = FallbackAiProvider(
        [
            StubProvider("claude-agent-sdk", error=AiProviderErrorKind.UNAVAILABLE),
            StubProvider("ollama", error=AiProviderErrorKind.TIMEOUT),
        ]
    )

    response = client_for(chain).post("/v1/clinical-extractions", json=REQUEST)

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    validator("Problem").validate(response.json())
    assert response.json()["code"] == "extraction_unavailable"
