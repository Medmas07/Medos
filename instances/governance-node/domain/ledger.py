"""What an audit ledger may anchor (HC-190): a minimized proof of a governance decision.

A proof payload holds references, an outcome, a time, organizations, and a version, and
nothing else: the type has no field for a patient reference, a purpose, a rationale, a
data scope, or any clinical content, so none can reach a ledger through it. Only a
recorded decision is anchored; requests received and authorization checks are not.
"""

from dataclasses import dataclass
from datetime import datetime

from domain.audit import AuditAction, AuditEvent, AuditOutcome

# The version of the payload's shape, anchored with it.
PAYLOAD_VERSION = 1


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
