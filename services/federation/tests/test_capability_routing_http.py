import json

import httpx
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_NOW, DEMO_SEED, contract, validator
from tests.test_http_node_descriptor_client import HOSPITAL_B
from tests.test_node_answer_parsing import FOUND

QUERY_CONTRACT = contract("federated-patient-query.v1.yaml")
OPERATION = QUERY_CONTRACT["paths"]["/v1/federated-queries"]["post"]
ROUTED = OPERATION["responses"]["200"]["content"]["application/json"]["examples"][
    "routedAroundNode"
]["value"]
GRANT_QUERY = OPERATION["requestBody"]["content"]["application/json"]["examples"][
    "drXTimeline"
]["value"] | {"scope": ["medications"]}
result_schema = validator(QUERY_CONTRACT, "FederatedQueryResult")


def live_like_network(request: httpx.Request) -> httpx.Response:
    """Test double shaped like the live demo: A has no endpoint, B answers, 8104 is down."""
    if request.url.port == 8101:
        return httpx.Response(404, json={"detail": "Not Found"})
    if request.url.port == 8102:
        if request.url.path == "/v1/federation/node":
            return httpx.Response(200, json=HOSPITAL_B)
        asked = json.loads(request.content)
        return httpx.Response(200, json=FOUND | {"query_id": asked["query_id"]})
    raise httpx.ConnectError("refused", request=request)


def api(node_mode="http"):
    transport = httpx.MockTransport(live_like_network)
    return TestClient(
        create_app(
            clock=lambda: DEMO_NOW,
            registry_seed=DEMO_SEED,
            node_transport=transport,
            node_mode=node_mode,
        )
    )


def query(client):
    response = client.post("/v1/federated-queries", json=GRANT_QUERY)
    errors = list(result_schema.iter_errors(response.json()))
    assert not errors, errors[0].message
    return response.json()


def test_after_discovery_the_query_reproduces_the_contract_example():
    client = api()
    client.post("/v1/registry/discovery")
    result = query(client)
    assert result["node_results"] == ROUTED["node_results"]
    assert [e["entry_ref"] for e in result["entries"]] == ["med-b-leila-coagulix"]
    assert result["notice"] == " ".join(ROUTED["notice"].split())


def test_without_discovery_every_node_is_asked():
    result = query(api())
    assert [r["status"] for r in result["node_results"]] == [
        "unavailable",
        "ok",
        "unavailable",
    ]


def test_a_node_moved_since_its_check_is_asked_again():
    client = api()
    client.post("/v1/registry/discovery")
    client.put(
        "/v1/registry/nodes/node-hospital-a",
        json={
            "organization_ref": "org-hospital-a",
            "base_url": "http://localhost:8111",
            "contract_versions": ["1.0"],
            "approval_decision_ref": "dec-hospital-a",
        },
    )
    assert query(client)["node_results"][0]["status"] == "unavailable"


def test_simulated_mode_ignores_discovery_of_real_addresses():
    client = api(node_mode="simulated")
    client.post("/v1/registry/discovery")
    assert query(client)["node_results"][0]["status"] == "ok"
