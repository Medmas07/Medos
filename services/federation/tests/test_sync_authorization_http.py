import copy

import httpx
import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_NOW, DEMO_SEED, contract, validator
from tests.test_http_sync_authorization_checker import AUTHORIZED, RESULTS

QUERY_CONTRACT = contract("federated-patient-query.v1.yaml")
OPERATION = QUERY_CONTRACT["paths"]["/v1/federated-queries"]["post"]
PROBLEMS = {
    status: OPERATION["responses"][status]["content"]["application/problem+json"][
        "examples"
    ]
    for status in ("403", "503")
}
result_schema = validator(QUERY_CONTRACT, "FederatedQueryResult")
problem_schema = validator(QUERY_CONTRACT, "Problem")

SYNC_QUERY = {
    "patient_ref": "pat-a",
    "scope": ["medications"],
    "purpose": AUTHORIZED["purpose"],
    "requested_by": {"organization_ref": "org-hospital-a", "actor_ref": "clin-x"},
    "authorization": {
        "basis": "synchronization_decision",
        "ref": "dec-sync-001",
        "expires_at": "2026-11-09T10:00:00+01:00",
    },
}


def api(governance):
    return TestClient(
        create_app(
            clock=lambda: DEMO_NOW,
            registry_seed=DEMO_SEED,
            governance_transport=httpx.MockTransport(governance),
        )
    )


def post(client, body):
    response = client.post("/v1/federated-queries", json=body)
    schema = result_schema if response.status_code == 200 else problem_schema
    errors = list(schema.iter_errors(response.json()))
    assert not errors, errors[0].message
    return response


def answering(value):
    def governance(request):
        return httpx.Response(200, json=value)

    return governance


def test_authorized_sync_asks_only_the_authorized_target():
    response = post(api(answering(AUTHORIZED)), SYNC_QUERY)
    assert response.status_code == 200
    result = response.json()
    assert [r["node_ref"] for r in result["node_results"]] == ["node-hospital-b"]
    # The node still enforces on its own. The simulated Hospital B only knows the
    # decisions in demo-data, and dec-sync-001 is created at runtime (demo step 20).
    assert result["node_results"][0]["status"] == "denied"


def test_governance_denial_is_a_403_with_its_reason():
    denied = RESULTS["rejected"]["value"] | {"decision_ref": "dec-sync-001"}
    response = post(api(answering(denied)), SYNC_QUERY)
    assert (response.status_code, response.json()["code"]) == (
        403,
        "authorization_denied",
    )
    assert response.json()["detail"].endswith(": not_approved.")


def test_unreachable_governance_is_a_503_matching_the_contract_example():
    def down(request):
        raise httpx.ConnectError("refused")

    response = post(api(down), SYNC_QUERY)
    expected = PROBLEMS["503"]["governanceUnavailable"]["value"]
    assert response.status_code == 503
    assert response.json()["detail"] == " ".join(expected["detail"].split())


def test_targets_outside_the_authorization_are_refused():
    body = copy.deepcopy(SYNC_QUERY)
    body["target_organization_refs"] = ["org-hospital-a"]
    response = post(api(answering(AUTHORIZED)), body)
    assert (response.status_code, response.json()["code"]) == (
        403,
        "authorization_denied",
    )
    assert "org-hospital-a" in response.json()["detail"]


@pytest.mark.parametrize(
    "governance",
    [
        answering(AUTHORIZED),
        lambda request: pytest.fail("Governance must not be asked"),
    ],
    ids=["governance_up", "governance_down"],
)
def test_patient_grants_do_not_go_through_governance(governance):
    grant_query = OPERATION["requestBody"]["content"]["application/json"]["examples"][
        "drXTimeline"
    ]["value"]
    response = post(api(governance), grant_query)
    assert response.json()["completeness"] == "partial"
