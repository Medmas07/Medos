"""Anchoring governance decisions in an audit ledger (HC-190 to HC-192), and the port.

The decision use cases anchor each decision they record through `anchor_recorded`;
the only adapter is the simulated ledger of HC-191 (MOCKED: in memory, not a
blockchain). A proof holds its payload's hash (HC-192), which `verify_proof` recomputes
against the audit trail. A real permissioned ledger (HC-194) is PLANNED behind this
port. Ledger technology is OPEN.
"""

from typing import Protocol

from application.audit import AuditTrail
from domain.audit import AuditEvent
from domain.ledger import (
    LedgerProof,
    ProofPayload,
    ProofVerification,
    proof_payload,
    verify,
)


class LedgerUnavailable(Exception):
    """The ledger could not be reached or refused to answer; nothing is anchored."""


class ProofNotFound(Exception):
    pass


class ProofConflict(Exception):
    """The event is already anchored with another payload."""


class AuditLedgerPort(Protocol):
    def anchor(self, payload: ProofPayload) -> LedgerProof:
        """Anchor the payload, append-only, and return the ledger's receipt, holding
        the payload's hash (domain.ledger.hash_payload). Raises LedgerUnavailable when
        nothing was anchored."""
        ...

    def proof(self, event_ref: str) -> LedgerProof | None:
        """The proof anchoring this event, if any. Raises LedgerUnavailable."""
        ...

    def proofs(self) -> list[LedgerProof]:
        """Every proof, in the order anchored. Raises LedgerUnavailable."""
        ...

    # Whether proofs are held by a simulation rather than a real ledger.
    simulated: bool


def anchor_decision(ledger: AuditLedgerPort, event: AuditEvent) -> LedgerProof:
    """Anchor a recorded decision once. Anchoring it again returns its proof; an event
    already anchored with another payload is a ProofConflict. Any other event is
    NotAnchorable."""
    payload = proof_payload(event)
    existing = ledger.proof(event.event_ref)
    if existing is not None:
        if existing.payload != payload:
            raise ProofConflict(event.event_ref)
        return existing
    return ledger.anchor(payload)


def anchor_recorded(
    ledger: AuditLedgerPort | None, event: AuditEvent
) -> LedgerProof | None:
    """Anchor a decision just recorded. The decision stands whatever happens: with no
    ledger, or the ledger unavailable, it stays unanchored and is not retried (OPEN)."""
    if ledger is None:
        return None
    try:
        return anchor_decision(ledger, event)
    except LedgerUnavailable:
        return None


def get_proof(event_ref: str, ledger: AuditLedgerPort) -> LedgerProof:
    proof = ledger.proof(event_ref)
    if proof is None:
        raise ProofNotFound(event_ref)
    return proof


def list_proofs(ledger: AuditLedgerPort) -> list[LedgerProof]:
    """Every proof, the latest anchored first."""
    return list(reversed(ledger.proofs()))


def verify_proof(proof: LedgerProof, trail: AuditTrail) -> ProofVerification:
    """Whether the proof's hash is its payload's and its audit event's, as the trail
    holds that event now."""
    return verify(proof, trail.event(proof.payload.event_ref))
