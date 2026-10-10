import httpx
import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_NOW, DEMO_SEED, contract, validator
from tests.test_http_node_descriptor_client import HOSPITAL_B

CONTRACT = contract("node-registry.v1.yaml")
DEMO = CONTRACT["paths"]["/v1/registry/discovery"]["post"]["responses"]["200"][
    "content"
]["application/json"]["examples"]["demoNodes"]["value"]
schemas = {
    name: validator(CONTRACT, name)
    for name in ("DiscoveryList", "DiscoveryResult", "Problem")
}


def checked(response, schema):
    errors = list(schemas[schema].iter_errors(response.json()))
    assert not errors, errors[0].message
    return response


def demo_nodes(request: httpx.Request) -> httpx.Response:
    """Test double for the network: what each demo port answers."""
    if request.url.port == 8101:  # Hospital Node runtime without a Federation interface
        return httpx.Response(404, json={"detail": "Not Found"})
    if request.url.port == 8102:
        return httpx.Response(200, json=HOSPITAL_B)
    raise httpx.ConnectError("refused", request=request)


@pytest.fixture
def api():
    app = create_app(
        clock=lambda: DEMO_NOW,
        registry_seed=DEMO_SEED,
        node_transport=httpx.MockTransport(demo_nodes),
        sleep=lambda seconds: None,
    )
    return TestClient(app)


def test_discovery_of_the_demo_nodes_matches_the_contract_example(api):
    body = checked(api.post("/v1/registry/discovery"), "DiscoveryList").json()
    assert body["notice"] == " ".join(DEMO["notice"].split())
    assert [
        (r["node_ref"], r["outcome"], r["capabilities"]) for r in body["results"]
    ] == [(r["node_ref"], r["outcome"], r["capabilities"]) for r in DEMO["results"]]


def test_nodes_are_not_checked_until_discovery_runs(api):
    before = checked(
        api.get("/v1/registry/nodes/node-hospital-b/capabilities"), "DiscoveryResult"
    )
    assert (before.json()["outcome"], before.json()["checked_at"]) == (
        "not_checked",
        None,
    )

    checked(
        api.post("/v1/registry/nodes/node-hospital-b/capabilities"), "DiscoveryResult"
    )
    after = checked(
        api.get("/v1/registry/nodes/node-hospital-b/capabilities"), "DiscoveryResult"
    )
    assert after.json()["outcome"] == "discovered"
    assert after.json()["capabilities"]["mocked"] is True


def test_moving_a_node_invalidates_its_result(api):
    api.post("/v1/registry/nodes/node-hospital-b/capabilities")
    api.put(
        "/v1/registry/nodes/node-hospital-b",
        json={
            "organization_ref": "org-hospital-b",
            "base_url": "http://localhost:8112",
            "contract_versions": ["1.0"],
            "approval_decision_ref": "dec-hospital-b",
        },
    )
    latest = checked(
        api.get("/v1/registry/nodes/node-hospital-b/capabilities"), "DiscoveryResult"
    )
    assert latest.json()["outcome"] == "not_checked"
    rechecked = checked(
        api.post("/v1/registry/nodes/node-hospital-b/capabilities"), "DiscoveryResult"
    )
    assert rechecked.json()["outcome"] == "unreachable"


def test_a_node_claiming_another_identity_is_flagged():
    def impostor(request):
        return httpx.Response(200, json=HOSPITAL_B | {"node_ref": "node-hospital-a"})

    api = TestClient(
        create_app(
            clock=lambda: DEMO_NOW,
            registry_seed=DEMO_SEED,
            node_transport=httpx.MockTransport(impostor),
            sleep=lambda seconds: None,
        )
    )
    result = checked(
        api.post("/v1/registry/nodes/node-hospital-b/capabilities"), "DiscoveryResult"
    )
    assert (result.json()["outcome"], result.json()["capabilities"]) == (
        "identity_mismatch",
        None,
    )


@pytest.mark.parametrize("method", ["get", "post"])
def test_unknown_node_returns_404(api, method):
    response = getattr(api, method)("/v1/registry/nodes/node-hospital-c/capabilities")
    checked(response, "Problem")
    assert (response.status_code, response.json()["code"]) == (404, "node_not_found")


def test_discovery_with_an_empty_registry_returns_no_results():
    api = TestClient(create_app(clock=lambda: DEMO_NOW))
    assert (
        checked(api.post("/v1/registry/discovery"), "DiscoveryList").json()["results"]
        == []
    )


def test_discovery_does_not_change_the_registry(api):
    api.post("/v1/registry/discovery")
    assert [n["node_ref"] for n in api.get("/v1/registry/nodes").json()["nodes"]] == [
        "node-hospital-a",
        "node-hospital-b",
        "node-private-practice",
    ]
