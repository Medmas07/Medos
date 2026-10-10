from typing import Protocol

from domain.audit_event import AuditEvent, AuditQuery


class AuditLog(Protocol):
    """This node's own audit trail. Append-only: events are never changed or removed."""

    # False while events do not survive a restart (persistence is OPEN).
    durable: bool

    def record(self, event: AuditEvent) -> None:
        """Raises if the event cannot be kept; the caller must then disclose nothing."""
        ...

    def events(self, query: AuditQuery) -> tuple[AuditEvent, ...]:
        """Matching events, newest first, at most query.limit."""
        ...
