from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_serves_openapi_document():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Governance Node"


def test_exposes_only_documented_governance_node_routes():
    # Other governance APIs (HC-132 to HC-136) are PLANNED.
    assert set(client.get("/openapi.json").json()["paths"]) == {
        "/health",
        "/v1/hospital-applications",
        "/v1/hospital-applications/{application_ref}",
        "/v1/hospital-applications/{application_ref}/decision",
        "/v1/hospital-approvals/{decision_ref}",
    }


def test_unknown_route_returns_404():
    assert client.get("/does-not-exist").status_code == 404
