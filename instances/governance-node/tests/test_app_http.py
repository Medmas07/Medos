from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_serves_openapi_document():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Governance Node"


def test_exposes_only_documented_governance_node_routes():
    assert set(client.get("/openapi.json").json()["paths"]) == {
        "/health",
        "/v1/hospital-applications",
        "/v1/hospital-applications/{application_ref}",
        "/v1/hospital-applications/{application_ref}/decision",
        "/v1/hospital-approvals/{decision_ref}",
        "/v1/synchronization-requests",
        "/v1/synchronization-requests/{request_ref}",
        "/v1/synchronization-requests/{request_ref}/decision",
        "/v1/synchronization-authorizations/{decision_ref}/checks",
        "/v1/research-requests",
        "/v1/research-requests/{request_ref}",
        "/v1/research-requests/{request_ref}/decision",
        "/v1/research-authorizations/check",
        "/v1/audit/events",
        "/v1/audit/events/{event_ref}",
        "/v1/audit/events/{event_ref}/proof",
        "/v1/ledger/proofs",
        "/v1/policies",
        "/v1/policies/{policy_ref}",
    }


def test_unknown_route_returns_404():
    assert client.get("/does-not-exist").status_code == 404
