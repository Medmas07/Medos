from datetime import timedelta

import pytest

from application.ledger import (
    LedgerUnavailable,
    ProofConflict,
    ProofNotFound,
    anchor_decision,
    get_proof,
)
from domain.audit import AuditAction, AuditOutcome, SubjectType
from domain.ledger import LedgerProof, NotAnchorable
from tests.conftest import DEMO_NOW
from tests.test_ledger import decision_event


class FakeAuditLedger:
    """Test double at the AuditLedgerPort; not a ledger."""

    simulated = True

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.proofs: dict[str, LedgerProof] = {}

    def anchor(self, payload):
        if not self.available:
            raise LedgerUnavailable("down")
        proof = LedgerProof(
            proof_ref=f"proof-{len(self.proofs) + 1:03d}",
            payload=payload,
            ledger="test-double",
            anchored_at=DEMO_NOW + timedelta(seconds=5),
        )
        self.proofs[payload.event_ref] = proof
        return proof

    def proof(self, event_ref):
        if not self.available:
            raise LedgerUnavailable("down")
        return self.proofs.get(event_ref)


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
    assert len(ledger.proofs) == 1


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
    assert ledger.proofs == {}


def test_an_unavailable_ledger_anchors_nothing():
    ledger = FakeAuditLedger(available=False)

    with pytest.raises(LedgerUnavailable):
        anchor_decision(ledger, decision_event())
    assert ledger.proofs == {}


def test_an_event_without_proof_is_not_found():
    with pytest.raises(ProofNotFound):
        get_proof("evt-001", FakeAuditLedger())
