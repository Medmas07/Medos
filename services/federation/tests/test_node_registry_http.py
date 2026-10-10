import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_NOW, DEMO_SEED, contract, validator

CONTRACT = contract("node-registry.v1.yaml")
PUT = CONTRACT["paths"]["/v1/registry/nodes/{node_ref}"]["put"]
HOSPITAL_B = PUT["requestBody"]["content"]["application/json"]["examples"]["hospitalB"][
    "value"
]
schemas = {
    name: validator(CONTRACT, name)
    for name in ("NodeList", "NodeRegistration", "Problem")
}


def checked(response, schema):
    errors = list(schemas[schema].iter_errors(response.json()))
    assert not errors, errors[0].message
    if schema == "Problem":
        assert response.headers["content-type"] == "application/problem+json"
    return response


@pytest.fixture
def empty():
    return TestClient(create_app(clock=lambda: DEMO_NOW))


@pytest.fixture
def seeded():
    return TestClient(create_app(clock=lambda: DEMO_NOW, registry_seed=DEMO_SEED))


def test_empty_registry_lists_no_nodes(empty):
    body = checked(empty.get("/v1/registry/nodes"), "NodeList").json()
    assert body["nodes"] == []
    assert "not verified" in body["notice"]


def test_seeded_registry_lists_demo_nodes_with_unverified_approval(seeded):
    nodes = checked(seeded.get("/v1/registry/nodes"), "NodeList").json()["nodes"]
    assert [n["node_ref"] for n in nodes] == [
        "node-hospital-a",
        "node-hospital-b",
        "node-private-practice",
    ]
    assert {n["approval"]["verified"] for n in nodes} == {False}


def test_register_then_update_then_get(empty):
    created = checked(
        empty.put("/v1/registry/nodes/node-hospital-b", json=HOSPITAL_B),
        "NodeRegistration",
    )
    assert created.status_code == 201
    assert created.json()["approval"] == {
        "decision_ref": "dec-hospital-b",
        "verified": False,
    }

    moved = {**HOSPITAL_B, "base_url": "http://localhost:8112"}
    updated = checked(
        empty.put("/v1/registry/nodes/node-hospital-b", json=moved), "NodeRegistration"
    )
    assert updated.status_code == 200

    fetched = checked(
        empty.get("/v1/registry/nodes/node-hospital-b"), "NodeRegistration"
    ).json()
    assert fetched["base_url"] == "http://localhost:8112"


def test_second_node_for_an_organization_conflicts(seeded):
    response = checked(
        seeded.put("/v1/registry/nodes/node-b-2", json=HOSPITAL_B), "Problem"
    )
    assert (response.status_code, response.json()["code"]) == (
        409,
        "organization_already_registered",
    )
    assert "node-hospital-b" in response.json()["detail"]


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"contract_versions": ["2.0"]}, "supported: 1.0"),
        ({"base_url": "http://user:pw@localhost:8102"}, "base_url"),
        ({"contract_versions": []}, "contract_versions"),
        ({"approval_decision_ref": "Décision B"}, "approval_decision_ref"),
        ({"patients": ["pat-a"]}, "patients"),
    ],
    ids=[
        "unsupported_version",
        "credentials_in_url",
        "no_version",
        "bad_ref",
        "extra_field",
    ],
)
def test_invalid_registrations_return_400(empty, change, field):
    response = checked(
        empty.put("/v1/registry/nodes/node-hospital-b", json=HOSPITAL_B | change),
        "Problem",
    )
    assert (response.status_code, response.json()["code"]) == (400, "invalid_request")
    assert response.json()["title"] == "Invalid node registration"
    assert field in response.json()["detail"]
    assert checked(empty.get("/v1/registry/nodes"), "NodeList").json()["nodes"] == []


def test_invalid_node_ref_in_path_returns_400(empty):
    response = checked(empty.put("/v1/registry/nodes/-bad", json=HOSPITAL_B), "Problem")
    assert response.status_code == 400


def test_unknown_node_returns_404(seeded):
    for response in (
        seeded.get("/v1/registry/nodes/node-hospital-c"),
        seeded.delete("/v1/registry/nodes/node-hospital-c"),
    ):
        checked(response, "Problem")
        assert (response.status_code, response.json()["code"]) == (
            404,
            "node_not_found",
        )


def test_deregister_removes_the_node(seeded):
    response = seeded.delete("/v1/registry/nodes/node-hospital-a")
    assert (response.status_code, response.content) == (204, b"")
    assert seeded.get("/v1/registry/nodes/node-hospital-a").status_code == 404
