"""AuditTrail in memory, seeded from fictional demo data (HC-134).

Explicit D2 storage: the Governance Node keeps its own audit trail, but only in memory,
so events recorded at runtime are lost on restart (`durable` is false). Persistence,
retention, and anchoring proofs in a ledger are OPEN. At startup it reads the events of
demo-data/governance.json; the domain and outcome of a decision event come from the
decision it names. A file not marked fictional, or inconsistent, stops startup.
"""

import json
import re
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from adapters.outbound.in_memory_hospital_applications import SeedError
from domain.audit import (
    AuditAction,
    AuditDomain,
    AuditEvent,
    AuditOutcome,
    InvalidAuditEvent,
    SubjectType,
)

_NUMBERED = re.compile(r"evt-(\d+)")
# The domain of a decision, from the subject it decides.
_DECISION_DOMAINS = {
    "hospital_application": AuditDomain.HOSPITAL_APPROVAL,
    "synchronization_request": AuditDomain.SYNCHRONIZATION,
    "research_access_request": AuditDomain.RESEARCH,
}


class InMemoryAuditTrail:
    durable = False

    def __init__(self, events: list[AuditEvent]) -> None:
        self._events: list[AuditEvent] = []
        self._by_ref: dict[str, AuditEvent] = {}
        self._lock = threading.Lock()
        for event in events:
            if event.event_ref in self._by_ref:
                raise SeedError(f"{event.event_ref} is recorded twice")
            self._store(event)

    @classmethod
    def load(cls, path: Path) -> "InMemoryAuditTrail":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("fictional") is not True:
                raise SeedError(f"{path} is not marked fictional")
            decisions = {d["id"]: d for d in data["decisions"]}
            return cls([_event(raw, decisions) for raw in data["auditEvents"]])
        except SeedError:
            raise
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise SeedError(f"Cannot load audit events {path}: {error}") from error

    def events(self) -> list[AuditEvent]:
        with self._lock:
            return list(self._events)

    def event(self, event_ref: str) -> AuditEvent | None:
        with self._lock:
            return self._by_ref.get(event_ref)

    def append(self, new_event: Callable[[str], AuditEvent]) -> AuditEvent:
        with self._lock:
            numbers = [
                int(m.group(1))
                for ref in self._by_ref
                if (m := _NUMBERED.fullmatch(ref))
            ]
            event = new_event(f"evt-{max(numbers, default=0) + 1:03d}")
            self._store(event)
            return event

    def _store(self, event: AuditEvent) -> None:
        self._events.append(event)
        self._by_ref[event.event_ref] = event


def _event(raw: dict, decisions: dict[str, dict]) -> AuditEvent:
    recorded_at = datetime.fromisoformat(raw["at"])
    if recorded_at.tzinfo is None:
        raise SeedError(f"{raw['id']} has a time without UTC offset")
    action = AuditAction(raw["action"])
    subject_type = SubjectType(raw["subjectType"])
    outcome = None
    if subject_type is SubjectType.DECISION:
        decision = decisions.get(raw["subjectId"])
        if decision is None:
            raise SeedError(f"{raw['id']} names an unknown decision")
        domain = _DECISION_DOMAINS[decision["subjectType"]]
        outcome = AuditOutcome(decision["outcome"])
    elif subject_type is SubjectType.HOSPITAL_APPLICATION:
        domain = AuditDomain.HOSPITAL_APPROVAL
    elif subject_type is SubjectType.SYNCHRONIZATION_REQUEST:
        domain = AuditDomain.SYNCHRONIZATION
    else:
        domain = AuditDomain.RESEARCH
    try:
        return AuditEvent(
            event_ref=raw["id"],
            recorded_at=recorded_at,
            action=action,
            domain=domain,
            actor_ref=raw["actorId"],
            subject_type=subject_type,
            subject_ref=raw["subjectId"],
            outcome=outcome,
            reason=None,
            organization_refs=tuple(raw["organizationIds"]),
        )
    except InvalidAuditEvent as error:
        raise SeedError(f"{raw['id']}: {error}") from error
