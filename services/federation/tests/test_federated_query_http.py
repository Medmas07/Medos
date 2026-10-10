import copy

import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_NOW, DEMO_SEED, contract, validator

CONTRACT = contract("federated-patient-query.v1.yaml")
OPERATION = CONTRACT["paths"]["/v1/federated-queries"]["post"]
REQUESTS = OPERATION["requestBody"]["content"]["application/json"]["examples"]
RESULTS = OPERATION["responses"]["200"]["content"]["application/json"]["examples"]
result_schema = validator(CONTRACT, "FederatedQueryResult")
problem_schema = validator(CONTRACT, "Problem")

client = TestClient(
    create_app(clock=lambda: DEMO_NOW, registry_seed=DEMO_SEED, node_mode="simulated")
)


def post(body, app_client=client):
    response = app_client.post("/v1/federated-queries", json=body)
    schema = result_schema if response.status_code == 200 else problem_schema
    errors = list(schema.iter_errors(response.json()))
    assert not errors, errors[0].message
    if response.status_code != 200:
        assert response.headers["content-type"] == "application/problem+json"
    return response


@pytest.mark.parametrize(
    ("request_name", "result_name"),
    [
        ("drXTimeline", "partialTimeline"),
        ("drXHospitalBMedications", "completeHospitalB"),
    ],
)
def test_demo_requests_reproduce_the_contract_examples(request_name, result_name):
    expected = RESULTS[result_name]["value"]

    actual = post(REQUESTS[request_name]["value"]).json()

    assert actual["completeness"] == expected["completeness"]
    assert actual["node_results"] == expected["node_results"]
    assert [e["entry_ref"] for e in actual["entries"]] == [
        e["entry_ref"] for e in expected["entries"]
    ]
    assert actual["provenance"]["mocked"] is True


def test_partial_result_says_missing_entries_are_not_absence():
    notice = post(REQUESTS["drXTimeline"]["value"]).json()["notice"]
    assert notice.startswith("Partial history: 1 source")
    assert "not evidence of absence" in notice


def test_lab_reports_are_returned_when_in_scope():
    body = copy.deepcopy(REQUESTS["drXTimeline"]["value"])
    body["scope"] = ["lab_reports"]
    entries = post(body).json()["entries"]
    assert [e["entry_ref"] for e in entries] == ["lab-b-2026-leila", "lab-a-2024-leila"]


def test_node_refusal_appears_per_node():
    body = copy.deepcopy(REQUESTS["drXTimeline"]["value"])
    body["purpose"] = "Autre finalité"
    result = post(body).json()
    assert [r["status"] for r in result["node_results"]] == [
        "denied",
        "denied",
        "unavailable",
    ]
    assert result["entries"] == []


def test_expired_authorization_is_refused_before_any_node():
    body = copy.deepcopy(REQUESTS["drXTimeline"]["value"])
    body["authorization"] = {
        "basis": "synchronization_decision",
        "ref": "dec-sync-002",
        "expires_at": "2026-03-12T14:30:00+01:00",
    }
    response = post(body)
    assert (response.status_code, response.json()["code"]) == (
        403,
        "authorization_denied",
    )


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        (lambda b: b.pop("authorization"), "authorization"),
        (lambda b: b.update(scope=[]), "scope"),
        (lambda b: b.update(scope=["medications", "medications"]), "scope"),
        (lambda b: b.update(patient_ref="Patient A"), "patient_ref"),
        (lambda b: b.update(extra="x"), "extra"),
        (
            lambda b: b["authorization"].update(expires_at="2026-10-24T09:00:00"),
            "authorization.expires_at",
        ),
    ],
    ids=[
        "no_authorization",
        "empty_scope",
        "duplicate_scope",
        "name_in_ref",
        "unknown_field",
        "naive_datetime",
    ],
)
def test_invalid_requests_return_400(mutate, field):
    body = copy.deepcopy(REQUESTS["drXTimeline"]["value"])
    mutate(body)
    response = post(body)
    assert (response.status_code, response.json()["code"]) == (400, "invalid_request")
    assert field in response.json()["detail"]


def test_unapproved_target_is_rejected():
    body = copy.deepcopy(REQUESTS["drXTimeline"]["value"])
    body["target_organization_refs"] = ["org-hospital-c"]
    response = post(body)
    assert response.status_code == 400
    assert "org-hospital-c" in response.json()["detail"]


def test_empty_registry_returns_503():
    empty = TestClient(create_app(clock=lambda: DEMO_NOW))
    response = post(REQUESTS["drXTimeline"]["value"], empty)
    assert (response.status_code, response.json()["code"]) == (
        503,
        "federation_unavailable",
    )
    assert response.json()["detail"] == "No Hospital Node is registered."


def test_deregistered_node_is_no_longer_asked():
    app_client = TestClient(
        create_app(
            clock=lambda: DEMO_NOW, registry_seed=DEMO_SEED, node_mode="simulated"
        )
    )
    assert (
        app_client.delete("/v1/registry/nodes/node-private-practice").status_code == 204
    )
    result = post(REQUESTS["drXTimeline"]["value"], app_client).json()
    assert [r["node_ref"] for r in result["node_results"]] == [
        "node-hospital-a",
        "node-hospital-b",
    ]
    assert result["completeness"] == "complete"


def test_health_labels_the_mock():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert (body["nodes"], body["mocked"]) == ("simulated", True)
    assert "not node-to-node exchange" in body["notice"]
