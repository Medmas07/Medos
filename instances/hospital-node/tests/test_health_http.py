from fastapi.testclient import TestClient

from domain.node_status import SKELETON_NOTICE
from main import app

client = TestClient(app)


def test_health_reports_skeleton_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "node": "hospital-node",
        "version": "0.1.0",
        "capabilities": [],
        "notice": SKELETON_NOTICE,
    }


def test_health_rejects_non_get_methods():
    assert client.post("/health").status_code == 405
