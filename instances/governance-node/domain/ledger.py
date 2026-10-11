"""What an audit ledger may anchor (HC-190): a minimized proof of a governance decision.

A proof payload holds references, an outcome, a time, organizations, and a version, and
nothing else: the type has no field for a patient reference, a purpose, a rationale, a
data scope, or any clinical content, so none can reach a ledger through it. Only a
recorded decision is anchored; requests received and authorization checks are not.

Each payload is hashed (HC-192): the SHA-256 of its canonical JSON, the form
demo-data/check_fixtures.py hashes the demo proofs with. A proof's hash makes a change to
its payload, or to the audit event it anchors, evident; it is not a signature.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from domain.audit import AuditAction, AuditEvent, AuditOutcome

# The version of the payload's shape, anchored with it.
PAYLOAD_VERSION = 1
HASH_ALGORITHM = "SHA-256"


class NotAnchorable(ValueError):
    pass


@dataclass(frozen=True)
class ProofPayload:
    event_ref: str
    decision_ref: str
    outcome: AuditOutcome
    decided_at: datetime
    # The Authority first, then the organizations the decision concerns.
    organization_refs: tuple[str, ...]
    version: int = PAYLOAD_VERSION


@dataclass(frozen=True)
class LedgerProof:
    """A ledger's receipt for an anchored payload."""

    proof_ref: str
    payload: ProofPayload
    # Which ledger holds it, as the adapter names it.
    ledger: str
    anchored_at: datetime
    # The hash the ledger holds for the payload (hash_payload), lowercase hex.
    payload_hash: str
    hash_algorithm: str = HASH_ALGORITHM


class ProofVerification(Enum):
    """The demo proof explorer's states (HC-080)."""

    # The proof's hash is its payload's, and the payload is its audit event's.
    VERIFIED = "verified"
    # The proof's hash differs from its payload's, or from its audit event's payload.
    TAMPERED = "tampered"
    # The audit event it anchors is missing or is not a recorded decision.
    INCONSISTENT = "inconsistent"


def proof_payload(event: AuditEvent) -> ProofPayload:
    """The payload anchoring a recorded decision; any other event is NotAnchorable."""
    if event.action is not AuditAction.DECISION_RECORDED:
        raise NotAnchorable(f"{event.event_ref} is not a recorded decision")
    # A recorded decision always has an outcome (domain.audit rules).
    assert event.outcome is not None
    return ProofPayload(
        event_ref=event.event_ref,
        decision_ref=event.subject_ref,
        outcome=event.outcome,
        decided_at=event.recorded_at,
        organization_refs=event.organization_refs,
    )


def canonical_payload(payload: ProofPayload) -> str:
    """The payload as hashed: the field names of the demo proofs' `anchoredPayload`,
    keys sorted, no whitespace, non-ASCII kept as UTF-8, times as ISO 8601 with offset."""
    return json.dumps(
        {
            "eventId": payload.event_ref,
            "decisionId": payload.decision_ref,
            "outcome": payload.outcome.value,
            "decidedAt": payload.decided_at.isoformat(),
            "organizationIds": list(payload.organization_refs),
            "version": payload.version,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def hash_payload(payload: ProofPayload) -> str:
    return hashlib.sha256(canonical_payload(payload).encode("utf-8")).hexdigest()


def verify(proof: LedgerProof, event: AuditEvent | None) -> ProofVerification:
    """Recompute the proof's hash from its payload and from the audit event it anchors."""
    if proof.hash_algorithm != HASH_ALGORITHM or proof.payload_hash != hash_payload(
        proof.payload
    ):
        return ProofVerification.TAMPERED
    if event is None or event.event_ref != proof.payload.event_ref:
        return ProofVerification.INCONSISTENT
    try:
        anchored = proof_payload(event)
    except NotAnchorable:
        return ProofVerification.INCONSISTENT
    if hash_payload(anchored) != proof.payload_hash:
        return ProofVerification.TAMPERED
    return ProofVerification.VERIFIED
