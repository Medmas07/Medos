from datetime import timedelta

import pytest

from application.ledger import (
    LedgerUnavailable,
    ProofConflict,
    ProofNotFound,
    anchor_decision,
    anchor_recorded,
    get_proof,
    list_proofs,
    verify_proof,
)
from domain.audit import AuditAction, AuditOutcome, SubjectType
from domain.ledger import LedgerProof, NotAnchorable, ProofVerification, hash_payload
from tests.conftest import DEMO_NOW
from tests.test_ledger import decision_event


class FakeAuditLedger:
    """Test double at the AuditLedgerPort; not a ledger."""

    simulated = True

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.anchored: dict[str, LedgerProof] = {}

    def anchor(self, payload):
        if not self.available:
            raise LedgerUnavailable("down")
        proof = LedgerProof(
            proof_ref=f"proof-{len(self.anchored) + 1:03d}",
            payload=payload,
            ledger="test-double",
            anchored_at=DEMO_NOW + timedelta(seconds=5),
            payload_hash=hash_payload(payload),
        )
        self.anchored[payload.event_ref] = proof
        return proof

    def proof(self, event_ref):
        if not self.available:
            raise LedgerUnavailable("down")
        return self.anchored.get(event_ref)

    def proofs(self):
        if not self.available:
            raise LedgerUnavailable("down")
        return list(self.anchored.values())


def test_a_recorded_decision_is_anchored_with_its_minimized_payload():
    ledger = FakeAuditLedger()

    proof = anchor_decision(ledger, decision_event())

    assert proof.proof_ref == "proof-001"
    assert proof.payload.decision_ref == "dec-sync-001"
    assert get_proof("evt-042", ledger) == proof


def test_anchoring_the_same_decision_again_returns_its_proof():
    ledger = FakeAuditLedger()
    first = anchor_decision(ledger, decision_event())

    assert anchor_decision(ledger, decision_event()) == first
    assert len(ledger.anchored) == 1


def test_an_event_anchored_with_another_payload_is_a_conflict():
    ledger = FakeAuditLedger()
    anchor_decision(ledger, decision_event())

    with pytest.raises(ProofConflict):
        anchor_decision(ledger, decision_event(outcome=AuditOutcome.REJECTED))


def test_an_event_other_than_a_decision_is_not_anchored():
    ledger = FakeAuditLedger()
    request = decision_event(
        action=AuditAction.REQUEST_RECEIVED,
        subject_type=SubjectType.SYNCHRONIZATION_REQUEST,
        subject_ref="sync-001",
        outcome=None,
    )

    with pytest.raises(NotAnchorable):
        anchor_decision(ledger, request)
    assert ledger.anchored == {}


def test_an_unavailable_ledger_anchors_nothing():
    ledger = FakeAuditLedger(available=False)

    with pytest.raises(LedgerUnavailable):
        anchor_decision(ledger, decision_event())
    assert ledger.anchored == {}


def test_an_event_without_proof_is_not_found():
    with pytest.raises(ProofNotFound):
        get_proof("evt-001", FakeAuditLedger())


def test_proofs_are_listed_the_latest_anchored_first():
    ledger = FakeAuditLedger()
    anchor_decision(ledger, decision_event())
    anchor_decision(ledger, decision_event(event_ref="evt-043"))

    assert [p.proof_ref for p in list_proofs(ledger)] == ["proof-002", "proof-001"]


def test_a_decision_just_recorded_is_anchored():
    ledger = FakeAuditLedger()

    proof = anchor_recorded(ledger, decision_event())

    assert proof == get_proof("evt-042", ledger)


def test_a_decision_stands_unanchored_without_a_ledger_or_when_it_is_unavailable():
    assert anchor_recorded(None, decision_event()) is None

    ledger = FakeAuditLedger(available=False)
    assert anchor_recorded(ledger, decision_event()) is None
    assert ledger.anchored == {}


class FakeTrail:
    """Test double at the AuditTrail port: only event() is used."""

    def __init__(self, *events) -> None:
        self._events = {e.event_ref: e for e in events}

    def event(self, event_ref):
        return self._events.get(event_ref)


def test_a_proof_of_its_audit_event_is_verified():
    proof = anchor_decision(FakeAuditLedger(), decision_event())

    assert (
        verify_proof(proof, FakeTrail(decision_event())) is ProofVerification.VERIFIED
    )


def test_an_audit_event_changed_after_anchoring_makes_its_proof_tampered():
    proof = anchor_decision(FakeAuditLedger(), decision_event())
    changed = decision_event(outcome=AuditOutcome.REJECTED)

    assert verify_proof(proof, FakeTrail(changed)) is ProofVerification.TAMPERED


def test_a_proof_of_a_missing_audit_event_is_inconsistent():
    proof = anchor_decision(FakeAuditLedger(), decision_event())

    assert verify_proof(proof, FakeTrail()) is ProofVerification.INCONSISTENT
