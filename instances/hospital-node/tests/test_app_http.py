from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_serves_openapi_document():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Hospital Node"


def test_exposes_only_health_federation_audit_and_access_grant_routes():
    assert set(client.get("/openapi.json").json()["paths"]) == {
        "/health",
        "/v1/federation/node",
        "/v1/federation/queries",
        "/v1/audit/events",
        "/v1/patients/{patient_ref}/access-grants",
        "/v1/patients/{patient_ref}/access-grants/{grant_ref}/revocation",
    }


def test_unknown_route_returns_404():
    assert client.get("/does-not-exist").status_code == 404
