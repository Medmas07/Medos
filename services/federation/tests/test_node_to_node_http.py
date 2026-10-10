import json

import httpx
import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_NOW, DEMO_SEED, contract, validator
from tests.test_node_answer_parsing import FOUND

QUERY_CONTRACT = contract("federated-patient-query.v1.yaml")
REQUEST = QUERY_CONTRACT["paths"]["/v1/federated-queries"]["post"]["requestBody"][
    "content"
]["application/json"]["examples"]["drXTimeline"]["value"]
result_schema = validator(QUERY_CONTRACT, "FederatedQueryResult")


def network(hospital_b_mocked=True, hospital_b=None):
    """Test double for the network, shaped like the live setup."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.port == 8101:  # Hospital Node runtime without the endpoint yet
            return httpx.Response(404, json={"detail": "Not Found"})
        if request.url.port == 8102:
            if hospital_b:
                return hospital_b(request)
            asked = json.loads(request.content)
            answer = FOUND | {"query_id": asked["query_id"]}
            answer["provenance"] = FOUND["provenance"] | {"mocked": hospital_b_mocked}
            return httpx.Response(200, json=answer)
        raise httpx.ConnectError("refused", request=request)

    return httpx.MockTransport(handler)


def api(transport):
    return TestClient(
        create_app(
            clock=lambda: DEMO_NOW, registry_seed=DEMO_SEED, node_transport=transport
        )
    )


def timeline(client):
    response = client.post("/v1/federated-queries", json=REQUEST)
    assert response.status_code == 200
    errors = list(result_schema.iter_errors(response.json()))
    assert not errors, errors[0].message
    return response.json()


def test_real_mode_reports_each_node_as_it_answered():
    result = timeline(api(network()))
    assert [(r["node_ref"], r["status"]) for r in result["node_results"]] == [
        ("node-hospital-a", "unavailable"),
        ("node-hospital-b", "ok"),
        ("node-private-practice", "unavailable"),
    ]
    assert [e["entry_ref"] for e in result["entries"]] == ["med-b-leila-coagulix"]
    assert result["completeness"] == "partial"


@pytest.mark.parametrize("node_mocked", [True, False])
def test_provenance_follows_what_the_nodes_said(node_mocked):
    result = timeline(api(network(hospital_b_mocked=node_mocked)))
    assert result["provenance"]["mocked"] is node_mocked


def test_a_misbehaving_node_contributes_nothing():
    def leaky(request):
        asked = json.loads(request.content)
        answer = FOUND | {"query_id": asked["query_id"]}
        answer["entries"] = [
            FOUND["entries"][0]
            | {
                "medication": FOUND["entries"][0]["medication"]
                | {"patient_name": "Leïla"}
            }
        ]
        return httpx.Response(200, json=answer)

    result = timeline(api(network(hospital_b=leaky)))
    assert result["node_results"][1]["status"] == "unavailable"
    assert result["entries"] == []


def test_a_slow_node_times_out_without_hiding_the_others():
    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    result = timeline(api(network(hospital_b=slow)))
    assert [r["status"] for r in result["node_results"]] == [
        "unavailable",
        "timeout",
        "unavailable",
    ]


def test_health_reports_real_mode():
    body = api(network()).get("/health").json()
    assert (body["nodes"], body["mocked"]) == ("http", False)
    assert "real HTTP" in body["notice"]


def test_unknown_node_mode_stops_startup():
    with pytest.raises(ValueError):
        create_app(node_mode="fake")
