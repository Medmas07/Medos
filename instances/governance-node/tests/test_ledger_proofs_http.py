"""The ledger proofs API against contracts/api/governance/governance-ledger-proofs.v1.yaml.

Every response is checked against the contract schema for its status, and the
contract's examples are the expected answers on the demo data. Each decision recorded
through the governance APIs is anchored in the simulated ledger at once (MOCKED).
"""

from dataclasses import replace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapters.inbound.http.authentication import AccessControl
from adapters.inbound.http.ledger_proofs import create_router
from adapters.outbound.fixture_reviewer_directory import FixtureReviewerDirectory
from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from adapters.outbound.simulated_audit_ledger import SimulatedAuditLedger
from application.ledger import LedgerUnavailable
from main import DEMO_IDENTITY, create_app
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_hospital_approval_http import APPROVE_C
from tests.test_research_http import APPROVE_002
from tests.test_synchronization_http import APPROVE_001, ASK_A, Clock, check, example
from tests.test_synchronization_http import load as load_contract

PROOFS = load_contract("api/governance/governance-ledger-proofs.v1.yaml")
LIST = PROOFS["paths"]["/v1/ledger/proofs"]["get"]
DETAIL = PROOFS["paths"]["/v1/audit/events/{event_ref}/proof"]["get"]
# Authentication off: readers are not checked.
OPEN = AccessControl(
    None, FixtureReviewerDirectory.load(DEMO_DATA / "people.json"), lambda: DEMO_NOW
)
# Anything a proof must never carry, at any depth of the answer.
FORBIDDEN = {"patient_ref", "actor_ref", "purpose", "rationale", "scope", "data_scope"}


@pytest.fixture
def client() -> TestClient:
    # A fresh app per test: each keeps its own ledger in memory.
    return TestClient(create_app(demo_data=DEMO_DATA, clock=Clock()))


def proof_of(client, event_ref: str) -> dict:
    return check(client.get(f"/v1/audit/events/{event_ref}/proof"), PROOFS, DETAIL, 200)


def decision_event(client, decision_ref: str) -> str:
    events = client.get(
        f"/v1/audit/events?subject_ref={decision_ref}&action=decision_recorded"
    ).json()["events"]
    assert len(events) == 1
    return events[0]["event_ref"]


def keys(node) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in keys(v)}
    return set()


def test_lists_the_simulated_seed_proofs_latest_first(client):
    body = check(client.get("/v1/ledger/proofs"), PROOFS, LIST, 200)

    assert body == example(PROOFS, LIST, 200, "seed")
    assert body["simulated"] is True
    assert "MOCKED BLOCKCHAIN" in body["notice"]


def test_reads_the_proof_of_an_audit_event(client):
    assert proof_of(client, "evt-004") == example(PROOFS, DETAIL, 200, "evt004")


@pytest.mark.parametrize(
    "event_ref, name",
    [
        ("evt-999", "unknownEvent"),
        # A request received: never anchored.
        ("evt-007", "notAnchored"),
    ],
)
def test_an_unknown_or_unanchored_event_has_no_proof(client, event_ref, name):
    response = client.get(f"/v1/audit/events/{event_ref}/proof")

    assert check(response, PROOFS, DETAIL, 404) == example(PROOFS, DETAIL, 404, name)


def test_a_seed_decision_the_demo_ledger_does_not_hold_has_no_proof(client):
    body = check(client.get("/v1/audit/events/evt-001/proof"), PROOFS, DETAIL, 404)

    assert body["code"] == "proof_not_found"


def test_a_synchronization_decision_is_anchored_as_it_is_recorded(client):
    decided = client.post(
        "/v1/synchronization-requests/sync-001/decision", json=APPROVE_001
    )
    assert decided.status_code == 201

    assert proof_of(client, "evt-008") == example(
        PROOFS, DETAIL, 200, "anchoredAtRuntime"
    )
    listed = check(client.get("/v1/ledger/proofs"), PROOFS, LIST, 200)["proofs"]
    assert [p["proof_ref"] for p in listed] == ["proof-005", "proof-004", "proof-003"]


@pytest.mark.parametrize(
    "path, body",
    [
        ("/v1/hospital-applications/app-hospital-c/decision", APPROVE_C),
        ("/v1/research-requests/rar-002/decision", APPROVE_002),
    ],
)
def test_hospital_approval_and_research_decisions_are_anchored(client, path, body):
    decision = client.post(path, json=body)
    assert decision.status_code == 201, decision.text
    decision_ref = decision.json()["decision_ref"]

    proof = proof_of(client, decision_event(client, decision_ref))["proof"]

    assert proof["payload"]["decision_ref"] == decision_ref
    assert proof["payload"]["outcome"] == "approved"
    assert proof["payload"]["organization_refs"][0] == "org-governance"
    assert proof["ledger"] == "local-simulation"


def test_a_proof_carries_only_the_minimized_payload(client):
    client.post("/v1/synchronization-requests/sync-001/decision", json=APPROVE_001)

    body = client.get("/v1/ledger/proofs").json()

    assert not keys(body["proofs"]) & FORBIDDEN
    assert "pat-a" not in str(body)
    assert all(
        set(p["payload"])
        == {
            "event_ref",
            "decision_ref",
            "outcome",
            "decided_at",
            "organization_refs",
            "version",
        }
        for p in body["proofs"]
    )


def test_a_refused_decision_or_an_authorization_check_anchors_nothing(client):
    refused = client.post(
        "/v1/synchronization-requests/sync-001/decision",
        json={**APPROVE_001, "reviewer_ref": "clin-x"},
    )
    assert refused.status_code == 403
    checked = client.post(
        "/v1/synchronization-authorizations/dec-sync-002/checks", json=ASK_A
    )
    assert checked.status_code == 200

    # The check was audited as evt-008, and is not a decision.
    assert client.get("/v1/audit/events/evt-008").status_code == 200
    assert (
        client.get("/v1/audit/events/evt-008/proof").json()["code"] == "proof_not_found"
    )
    assert len(client.get("/v1/ledger/proofs").json()["proofs"]) == 2


def test_proofs_anchored_at_runtime_are_lost_on_restart(client):
    client.post("/v1/synchronization-requests/sync-001/decision", json=APPROVE_001)

    restarted = TestClient(create_app(demo_data=DEMO_DATA, clock=Clock()))

    assert len(restarted.get("/v1/ledger/proofs").json()["proofs"]) == 2


class UnavailableLedger:
    simulated = True

    def anchor(self, payload):
        raise LedgerUnavailable("down")

    def proof(self, event_ref):
        raise LedgerUnavailable("down")

    def proofs(self):
        raise LedgerUnavailable("down")


def test_an_unavailable_ledger_answers_503():
    app = FastAPI()
    trail = InMemoryAuditTrail.load(DEMO_DATA / "governance.json")
    app.include_router(create_router(DEMO_IDENTITY, UnavailableLedger(), trail, OPEN))
    client = TestClient(app)

    for path, operation in [
        ("/v1/ledger/proofs", LIST),
        ("/v1/audit/events/evt-004/proof", DETAIL),
    ]:
        assert check(client.get(path), PROOFS, operation, 503)["code"] == (
            "ledger_unavailable"
        )


def test_every_proof_carries_its_payload_hash_verified_against_the_trail(client):
    client.post("/v1/synchronization-requests/sync-001/decision", json=APPROVE_001)

    proofs = check(client.get("/v1/ledger/proofs"), PROOFS, LIST, 200)["proofs"]

    assert all(p["hash_algorithm"] == "SHA-256" for p in proofs)
    assert all(p["verification"] == "verified" for p in proofs)
    assert len({p["payload_hash"] for p in proofs}) == 3


def test_a_proof_whose_hash_is_not_its_payloads_is_served_as_tampered():
    trail = InMemoryAuditTrail.load(DEMO_DATA / "governance.json")
    seeded = SimulatedAuditLedger.load(
        DEMO_DATA / "governance.json", trail, lambda: DEMO_NOW
    )
    forged = SimulatedAuditLedger(
        lambda: DEMO_NOW,
        [replace(p, payload_hash="0" * 64) for p in seeded.proofs()],
    )
    app = FastAPI()
    app.include_router(create_router(DEMO_IDENTITY, forged, trail, OPEN))

    proof = proof_of(TestClient(app), "evt-004")["proof"]

    assert proof["verification"] == "tampered"
    assert proof["payload_hash"] == "0" * 64
