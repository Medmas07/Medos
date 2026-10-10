from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_serves_openapi_document():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Hospital Node"


def test_exposes_no_product_routes_yet():
    assert client.get("/openapi.json").json()["paths"] == {}


def test_unknown_route_returns_404():
    assert client.get("/does-not-exist").status_code == 404
