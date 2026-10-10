from fastapi.testclient import TestClient

from main import app
from tests.test_research_http import request


client = TestClient(app)


def test_unconfigured_runtime_is_visibly_degraded_and_fails_closed():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "degraded"
    assert health.json()["mocked"] is False

    submitted = client.post(
        "/v1/research-jobs", json=request("job-runtime-unconfigured")
    )
    assert submitted.status_code == 202
    assert submitted.json()["status"] == "failed"
    assert submitted.json()["error"] == {
        "code": "governance_unavailable",
        "message": "Governance authorization could not be verified.",
        "retryable": True,
    }
    assert submitted.json()["executions"] == []
