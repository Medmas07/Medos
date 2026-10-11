import importlib.util
import json
from dataclasses import fields, replace
from datetime import datetime

import pytest

from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from domain.audit import (
    AuditAction,
    AuditDomain,
    AuditEvent,
    AuditOutcome,
    SubjectType,
)
from domain.ledger import (
    LedgerProof,
    NotAnchorable,
    ProofPayload,
    ProofVerification,
    canonical_payload,
    hash_payload,
    proof_payload,
    verify,
)
from tests.conftest import DEMO_DATA, DEMO_NOW

# The fields a demo ledger proof may anchor (demo-data/check_fixtures.py
# ALLOWED_PROOF_FIELDS), by this payload's names; the actor is not anchored.
ANCHORED = {
    "event_ref",
    "decision_ref",
    "outcome",
    "decided_at",
    "organization_refs",
    "version",
}


def decision_event(**overrides) -> AuditEvent:
    values = dict(
        event_ref="evt-042",
        recorded_at=DEMO_NOW,
        action=AuditAction.DECISION_RECORDED,
        domain=AuditDomain.SYNCHRONIZATION,
        actor_ref="usr-olfa",
        subject_type=SubjectType.DECISION,
        subject_ref="dec-sync-001",
        outcome=AuditOutcome.APPROVED,
        reason=None,
        organization_refs=("org-governance", "org-hospital-a", "org-hospital-b"),
    )
    return AuditEvent(**(values | overrides))


def test_a_recorded_decision_gives_a_payload_of_references_only():
    payload = proof_payload(decision_event())

    assert payload == ProofPayload(
        event_ref="evt-042",
        decision_ref="dec-sync-001",
        outcome=AuditOutcome.APPROVED,
        decided_at=DEMO_NOW,
        organization_refs=("org-governance", "org-hospital-a", "org-hospital-b"),
        version=1,
    )


def test_the_payload_has_exactly_the_fields_a_demo_proof_may_anchor():
    assert {f.name for f in fields(ProofPayload)} == ANCHORED


@pytest.mark.parametrize(
    "event",
    [
        decision_event(
            action=AuditAction.REQUEST_RECEIVED,
            subject_type=SubjectType.SYNCHRONIZATION_REQUEST,
            subject_ref="sync-001",
            outcome=None,
        ),
        decision_event(
            action=AuditAction.AUTHORIZATION_CHECKED,
            outcome=AuditOutcome.DENIED,
            reason="revoked",
        ),
    ],
)
def test_only_a_recorded_decision_is_anchorable(event):
    with pytest.raises(NotAnchorable):
        proof_payload(event)


@pytest.mark.parametrize("event_ref", ["evt-003", "evt-004"])
def test_seed_decisions_give_the_payloads_of_the_demo_proofs(event_ref):
    trail = InMemoryAuditTrail.load(DEMO_DATA / "governance.json")
    proofs = json.loads((DEMO_DATA / "governance.json").read_text(encoding="utf-8"))[
        "ledgerProofs"
    ]
    anchored = next(p for p in proofs if p["auditEventId"] == event_ref)[
        "anchoredPayload"
    ]

    payload = proof_payload(trail.event(event_ref))

    assert {
        "eventId": payload.event_ref,
        "decisionId": payload.decision_ref,
        "outcome": payload.outcome.value,
        "decidedAt": payload.decided_at,
        "organizationIds": list(payload.organization_refs),
        "version": payload.version,
    } == anchored | {"decidedAt": datetime.fromisoformat(anchored["decidedAt"])}


def _check_fixtures():
    spec = importlib.util.spec_from_file_location(
        "check_fixtures", DEMO_DATA / "check_fixtures.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proof(event, **overrides) -> LedgerProof:
    payload = proof_payload(event)
    values = dict(
        proof_ref="proof-042",
        payload=payload,
        ledger="test",
        anchored_at=DEMO_NOW,
        payload_hash=hash_payload(payload),
    )
    return LedgerProof(**(values | overrides))


def test_the_canonical_payload_is_sorted_compact_json_of_the_demo_field_names():
    assert canonical_payload(proof_payload(decision_event())) == (
        '{"decidedAt":"2026-10-10T10:00:00+01:00","decisionId":"dec-sync-001",'
        '"eventId":"evt-042","organizationIds":["org-governance","org-hospital-a",'
        '"org-hospital-b"],"outcome":"approved","version":1}'
    )


@pytest.mark.parametrize("event_ref", ["evt-003", "evt-004"])
def test_seed_decisions_hash_to_the_demo_proofs_hashes(event_ref):
    trail = InMemoryAuditTrail.load(DEMO_DATA / "governance.json")
    proofs = json.loads((DEMO_DATA / "governance.json").read_text(encoding="utf-8"))[
        "ledgerProofs"
    ]
    demo = next(p for p in proofs if p["auditEventId"] == event_ref)

    assert demo["hashAlgorithm"] == "SHA-256"
    assert hash_payload(proof_payload(trail.event(event_ref))) == demo["hash"]


def test_the_hash_is_the_one_check_fixtures_computes_also_for_non_ascii_refs():
    payload = replace(proof_payload(decision_event()), decision_ref="dec-é-001")
    anchored = json.loads(canonical_payload(payload))

    assert hash_payload(payload) == _check_fixtures().proof_hash(anchored)


def test_a_proof_of_its_audit_event_is_verified():
    assert verify(_proof(decision_event()), decision_event()) is (
        ProofVerification.VERIFIED
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"payload_hash": "0" * 64},
        {"hash_algorithm": "MD5"},
        # The payload changed, its hash not.
        {"payload": proof_payload(decision_event(outcome=AuditOutcome.REJECTED))},
    ],
)
def test_a_hash_that_is_not_its_payloads_is_tampered(overrides):
    proof = _proof(decision_event(), **overrides)

    assert verify(proof, decision_event()) is ProofVerification.TAMPERED


def test_an_audit_event_that_no_longer_gives_the_payload_is_tampered():
    changed = decision_event(organization_refs=("org-governance", "org-hospital-a"))

    assert verify(_proof(decision_event()), changed) is ProofVerification.TAMPERED


@pytest.mark.parametrize(
    "event",
    [
        None,
        decision_event(event_ref="evt-043"),
        decision_event(
            action=AuditAction.AUTHORIZATION_CHECKED,
            outcome=AuditOutcome.DENIED,
            reason="revoked",
        ),
    ],
)
def test_a_proof_without_its_recorded_decision_is_inconsistent(event):
    assert verify(_proof(decision_event()), event) is ProofVerification.INCONSISTENT
