import json

import httpx
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_NOW, DEMO_SEED, contract, validator
from tests.test_node_answer_parsing import FOUND

QUERY_CONTRACT = contract("federated-patient-query.v1.yaml")
REQUEST = QUERY_CONTRACT["paths"]["/v1/federated-queries"]["post"]["requestBody"][
    "content"
]["application/json"]["examples"]["drXTimeline"]["value"] | {"scope": ["medications"]}
result_schema = validator(QUERY_CONTRACT, "FederatedQueryResult")


class Network:
    """Test double: Hospital B drops every other connection; 8101 and 8104 are down."""

    def __init__(self):
        self.calls = {8101: 0, 8102: 0, 8104: 0}

    def __call__(self, request):
        port = request.url.port
        self.calls[port] += 1
        if port == 8102 and self.calls[port] % 2 == 0:
            asked = json.loads(request.content)
            return httpx.Response(200, json=FOUND | {"query_id": asked["query_id"]})
        if port == 8102:
            raise httpx.ConnectError("dropped", request=request)
        if port == 8101:
            return httpx.Response(503, json={"code": "node_unavailable"})
        raise httpx.ConnectError("refused", request=request)


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


def setup():
    network, clock = Network(), Clock()
    client = TestClient(
        create_app(
            clock=lambda: DEMO_NOW,
            registry_seed=DEMO_SEED,
            node_transport=httpx.MockTransport(network),
            breaker_clock=clock,
            sleep=lambda seconds: None,
        )
    )
    return client, network, clock


def statuses(client):
    response = client.post("/v1/federated-queries", json=REQUEST)
    errors = list(result_schema.iter_errors(response.json()))
    assert not errors, errors[0].message
    return [(r["status"], r["problem_code"]) for r in response.json()["node_results"]]


def test_a_dropped_connection_is_retried_and_dead_nodes_are_paused():
    client, network, clock = setup()

    for _ in range(3):
        assert statuses(client) == [
            ("unavailable", "node_unavailable"),
            ("ok", None),
            ("unavailable", "node_unavailable"),
        ]
    assert network.calls == {8101: 6, 8102: 6, 8104: 6}  # each tried twice per query

    assert statuses(client) == [
        ("not_asked", "circuit_open"),
        ("ok", None),
        ("not_asked", "circuit_open"),
    ]
    assert network.calls[8101] == 6 and network.calls[8104] == 6

    clock.now += 30
    assert statuses(client)[0] == ("unavailable", "node_unavailable")  # probed again


def test_simulated_mode_has_no_retries_or_breaker():
    client = TestClient(
        create_app(
            clock=lambda: DEMO_NOW, registry_seed=DEMO_SEED, node_mode="simulated"
        )
    )
    for _ in range(4):
        assert statuses(client)[2] == ("unavailable", "node_unavailable")
