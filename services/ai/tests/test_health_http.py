from fastapi.testclient import TestClient

from domain.service_status import ADVISORY_NOTICE
from main import app

client = TestClient(app)


def test_health_reports_skeleton_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-services",
        "version": "0.2.0",
        "capabilities": ["clinical-extraction:mocked"],
        "notice": ADVISORY_NOTICE,
    }


def test_unknown_route_returns_404():
    assert client.get("/does-not-exist").status_code == 404
