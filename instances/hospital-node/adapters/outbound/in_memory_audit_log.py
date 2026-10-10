"""This node's audit trail, kept in memory (HC-116).

Persistence is OPEN (ADR-0003), so events live only as long as the process: a restart
starts an empty trail, and nothing is written to storage_dir. Append-only. Events are
real records of the queries this node handled, not fixtures.
"""

from threading import Lock

from domain.audit_event import AuditEvent, AuditQuery


class InMemoryAuditLog:
    durable = False

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = Lock()

    def record(self, event: AuditEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events(self, query: AuditQuery) -> tuple[AuditEvent, ...]:
        with self._lock:
            newest_first = reversed(self._events)
            return tuple(e for e in newest_first if query.matches(e))[: query.limit]
