"""Governance audit use cases (HC-134) and the port they own.

The other use cases record their events through `record`: a request received, a
decision recorded, and every authorization check answered, authorized or denied.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from domain.audit import (
    AuditAction,
    AuditDomain,
    AuditEvent,
    AuditFilter,
    AuditOutcome,
    SubjectType,
)
from domain.research import AUTHORITY_ORGANIZATION_REF

__all__ = ["AUTHORITY_ORGANIZATION_REF"]

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


class EventNotFound(Exception):
    pass


class AuditTrail(Protocol):
    def events(self) -> list[AuditEvent]:
        """Every event, in the order recorded."""
        ...

    def event(self, event_ref: str) -> AuditEvent | None: ...

    def append(self, new_event: Callable[[str], AuditEvent]) -> AuditEvent:
        """Store the event built with the next free reference, and return it. The
        builder runs while the trail is locked and must not call the trail."""
        ...

    # Whether events survive a restart.
    durable: bool


def record(
    trail: AuditTrail,
    at: datetime,
    action: AuditAction,
    domain: AuditDomain,
    actor_ref: str | None,
    subject_type: SubjectType,
    subject_ref: str,
    organization_refs: tuple[str, ...],
    outcome: AuditOutcome | None = None,
    reason: str | None = None,
) -> AuditEvent:
    # dict.fromkeys drops repeated organizations and keeps their order.
    organizations = tuple(dict.fromkeys(organization_refs))
    return trail.append(
        lambda event_ref: AuditEvent(
            event_ref=event_ref,
            recorded_at=at,
            action=action,
            domain=domain,
            actor_ref=actor_ref,
            subject_type=subject_type,
            subject_ref=subject_ref,
            outcome=outcome,
            reason=reason,
            organization_refs=organizations,
        )
    )


def list_events(
    trail: AuditTrail, wanted: AuditFilter, limit: int = DEFAULT_LIMIT
) -> list[AuditEvent]:
    """Matching events, newest first; the later recorded first at the same time."""
    events = [e for e in reversed(trail.events()) if wanted.matches(e)]
    events.sort(key=lambda e: e.recorded_at, reverse=True)
    return events[:limit]


def get_event(event_ref: str, trail: AuditTrail) -> AuditEvent:
    event = trail.event(event_ref)
    if event is None:
        raise EventNotFound(event_ref)
    return event
