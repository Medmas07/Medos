from fastapi.testclient import TestClient

from domain.node_identity import NodeIdentity
from domain.node_status import SKELETON_NOTICE
from main import create_app

client = TestClient(create_app())


def test_health_reports_the_demo_governance_authority():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "node": "governance-node",
        "version": "0.9.0",
        "node_ref": "node-governance",
        "organization_ref": "org-governance",
        "capabilities": [
            "hospital_approval",
            "synchronization",
            "research",
            "audit",
            "policy",
            "ledger",
        ],
        # create_app's default: the MOCKED fixture grants (tests and demos).
        "grants": "fixture",
        # create_app's default without credentials: reviewers are declared (HC-211).
        "authentication": "off",
        "notice": SKELETON_NOTICE,
    }


def test_health_reports_the_identity_it_was_built_with():
    other = NodeIdentity(node_ref="node-gov-test", organization_ref="org-gov-test")

    body = TestClient(create_app(other)).get("/health").json()

    assert (body["node_ref"], body["organization_ref"]) == (
        "node-gov-test",
        "org-gov-test",
    )


def test_health_rejects_non_get_methods():
    assert client.post("/health").status_code == 405
