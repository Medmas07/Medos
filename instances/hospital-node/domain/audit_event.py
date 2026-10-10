"""This node's audit trail of patient history queries (HC-116).

An event says who asked for which patient's records, why, under which authorization,
and what the node did. It names disclosed records by reference only and never carries
clinical content. Shape: contracts/api/hospital-audit/hospital-audit-events.v1.yaml.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from domain.patient_history import (
    AuthorizationBasis,
    HistoryQuery,
    Requester,
    ScopeItem,
)


class InvalidAuditQuery(ValueError):
    pass


class AuditAction(Enum):
    PATIENT_HISTORY_QUERY = "patient_history_query"


class AuditOutcome(Enum):
    DISCLOSED = "disclosed"
    DENIED = "denied"


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    recorded_at: datetime
    action: AuditAction
    outcome: AuditOutcome
    query_id: str
    patient_ref: str
    requested_by: Requester
    purpose: str
    scope: frozenset[ScopeItem]
    authorization_basis: AuthorizationBasis
    authorization_ref: str
    # References of the records disclosed, never their content. Empty when denied.
    disclosed_entry_refs: tuple[str, ...] = ()

    @classmethod
    def of_query(
        cls,
        event_id: str,
        recorded_at: datetime,
        query: HistoryQuery,
        outcome: AuditOutcome,
        disclosed_entry_refs: tuple[str, ...] = (),
    ) -> "AuditEvent":
        return cls(
            event_id=event_id,
            recorded_at=recorded_at,
            action=AuditAction.PATIENT_HISTORY_QUERY,
            outcome=outcome,
            query_id=query.query_id,
            patient_ref=query.patient_ref,
            requested_by=query.requested_by,
            purpose=query.purpose,
            scope=query.scope,
            authorization_basis=query.authorization.basis,
            authorization_ref=query.authorization.ref,
            disclosed_entry_refs=disclosed_entry_refs,
        )


MAX_LIMIT = 500


@dataclass(frozen=True)
class AuditQuery:
    """Which events to list. Every filter is optional; results are newest first."""

    patient_ref: str | None = None
    query_id: str | None = None
    outcome: AuditOutcome | None = None
    limit: int = 50

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= MAX_LIMIT:
            raise InvalidAuditQuery(f"limit must be between 1 and {MAX_LIMIT}")

    def matches(self, event: AuditEvent) -> bool:
        return (
            self.patient_ref in (None, event.patient_ref)
            and self.query_id in (None, event.query_id)
            and self.outcome in (None, event.outcome)
        )
