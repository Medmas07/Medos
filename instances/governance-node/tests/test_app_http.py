from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_serves_openapi_document():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Governance Node"


def test_exposes_only_documented_governance_node_routes():
    # Governance APIs (HC-131 to HC-136) are PLANNED; none is served yet.
    assert set(client.get("/openapi.json").json()["paths"]) == {"/health"}


def test_unknown_route_returns_404():
    assert client.get("/does-not-exist").status_code == 404
