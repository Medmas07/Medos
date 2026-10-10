from fastapi.testclient import TestClient

from domain.service_status import ADVISORY_NOTICE
from infrastructure.settings import ExtractionMode, Settings
from main import create_app
from tests.conftest import fixture_client

client = fixture_client()


def test_health_reports_skeleton_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-services",
        "version": "0.3.0",
        "capabilities": ["clinical-extraction:mocked"],
        "notice": ADVISORY_NOTICE,
    }


def test_model_mode_reports_model_capability():
    app = create_app(Settings(extraction_mode=ExtractionMode.MODEL))

    capabilities = TestClient(app).get("/health").json()["capabilities"]

    assert capabilities == ["clinical-extraction:model"]


def test_unknown_route_returns_404():
    assert client.get("/does-not-exist").status_code == 404
