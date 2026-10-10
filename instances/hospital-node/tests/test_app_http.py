from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_serves_openapi_document():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Hospital Node"


def test_exposes_only_health_and_the_federation_interface():
    assert set(client.get("/openapi.json").json()["paths"]) == {
        "/health",
        "/v1/federation/node",
        "/v1/federation/queries",
    }


def test_unknown_route_returns_404():
    assert client.get("/does-not-exist").status_code == 404
