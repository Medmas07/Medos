import copy

import pytest

from adapters.outbound.simulated_hospital_nodes import SimulatedHospitalNodes
from tests.conftest import DEMO_NOW, contract, validator

NODE_CONTRACT = contract("hospital-node-federation.v1.yaml")
request_schema = validator(NODE_CONTRACT, "NodeQueryRequest")
result_schema = validator(NODE_CONTRACT, "NodeQueryResult")
problem_schema = validator(NODE_CONTRACT, "Problem")

NODES = SimulatedHospitalNodes(clock=lambda: DEMO_NOW).nodes

GRANT_REQUEST = {
    "query_id": "0b9f6c2e-3d41-4a8e-9f57-1c2d3e4f5a6b",
    "patient_ref": "pat-a",
    "scope": ["encounters", "medications", "lab_reports"],
    "purpose": "Consultation de cardiologie",
    "requested_by": {"organization_ref": "org-hospital-a", "actor_ref": "clin-x"},
    "authorization": {
        "basis": "patient_access_grant",
        "ref": "grant-a-drx",
        "expires_at": "2026-10-24T09:00:00+01:00",
    },
}


def changed(document, mutate):
    copied = copy.deepcopy(document)
    mutate(copied)
    return copied


def handle(organization, request):
    assert request_schema.is_valid(request)
    status, body = NODES[organization].handle(request)
    schema = result_schema if status == 200 else problem_schema
    errors = list(schema.iter_errors(body))
    assert not errors, errors[0].message
    return status, body


def test_each_node_discloses_only_records_it_holds():
    status, body = handle("org-hospital-b", GRANT_REQUEST)
    assert status == 200
    assert {e["entry_ref"] for e in body["entries"]} == {
        "enc-b-2026-leila",
        "med-b-leila-coagulix",
        "lab-b-2026-leila",
    }
    assert {e["source"]["organization_ref"] for e in body["entries"]} == {
        "org-hospital-b"
    }
    assert body["provenance"]["mocked"] is True


def test_only_the_requested_scope_is_disclosed():
    _, body = handle(
        "org-hospital-b",
        changed(GRANT_REQUEST, lambda r: r.update(scope=["medications"])),
    )
    assert [e["record_type"] for e in body["entries"]] == ["medication"]


def test_nothing_in_scope_is_an_empty_answer_not_an_error():
    request = changed(GRANT_REQUEST, lambda r: r.update(scope=["medications"]))
    status, body = handle("org-hospital-a", request)
    assert (status, body["entries"]) == (200, [])


def test_degraded_node_with_disconnected_dmi_is_unavailable():
    status, body = handle("org-private-practice", GRANT_REQUEST)
    assert (status, body["code"]) == (503, "node_unavailable")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["authorization"].update(ref="grant-a-ines"),
        lambda r: r["authorization"].update(ref="grant-c-ines"),
        lambda r: r["authorization"].update(ref="grant-unknown"),
        lambda r: r["requested_by"].update(actor_ref="clin-ines"),
        lambda r: r.update(purpose="Étude interne"),
        lambda r: r.update(patient_ref="pat-b"),
        lambda r: r["authorization"].update(basis="synchronization_decision"),
    ],
    ids=[
        "expired_grant",
        "revoked_grant",
        "unknown_grant",
        "other_actor",
        "other_purpose",
        "other_patient",
        "wrong_basis",
    ],
)
def test_nodes_deny_by_default(mutate):
    status, body = handle("org-hospital-b", changed(GRANT_REQUEST, mutate))
    assert (status, body["code"]) == (403, "authorization_denied")


def test_scope_wider_than_the_grant_is_denied():
    nodes = SimulatedHospitalNodes(clock=lambda: DEMO_NOW).nodes
    grant = nodes["org-hospital-b"]._grants["grant-a-drx"]
    grant["scope"] = ["medications"]
    status, _ = nodes["org-hospital-b"].handle(GRANT_REQUEST)
    assert status == 403


SYNC_REQUEST = {
    **GRANT_REQUEST,
    "patient_ref": "pat-c",
    "scope": ["encounters"],
    "purpose": "Suivi de l'asthme après passage aux urgences",
    "requested_by": {
        "organization_ref": "org-private-practice",
        "actor_ref": "clin-hatem",
    },
    "authorization": {
        "basis": "synchronization_decision",
        "ref": "dec-sync-002",
        "expires_at": "2026-03-12T14:30:00+01:00",
    },
}


def test_synchronization_decision_is_honoured_only_while_valid_and_by_the_target():
    before_expiry = SimulatedHospitalNodes(
        clock=lambda: DEMO_NOW.replace(year=2026, month=1)
    ).nodes
    status, body = before_expiry["org-hospital-b"].handle(SYNC_REQUEST)
    assert status == 200
    assert [e["entry_ref"] for e in body["entries"]] == ["enc-b-2025-nour"]
    assert before_expiry["org-hospital-a"].handle(SYNC_REQUEST)[0] == 403
    assert handle("org-hospital-b", SYNC_REQUEST)[0] == 403
