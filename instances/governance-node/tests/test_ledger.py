import json
from dataclasses import fields
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
from domain.ledger import NotAnchorable, ProofPayload, proof_payload
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
