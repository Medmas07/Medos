from datetime import datetime, timedelta

import pytest

from application.audit import EventNotFound, get_event, list_events, record
from domain.audit import (
    AuditAction,
    AuditDomain,
    AuditFilter,
    AuditOutcome,
    SubjectType,
)
from tests.conftest import DEMO_NOW


class FakeAuditTrail:
    """Test double at the AuditTrail port."""

    durable = False

    def __init__(self) -> None:
        self.recorded = []

    def events(self):
        return list(self.recorded)

    def event(self, event_ref):
        return next((e for e in self.recorded if e.event_ref == event_ref), None)

    def append(self, new_event):
        event = new_event(f"evt-{len(self.recorded) + 1:03d}")
        self.recorded.append(event)
        return event


def received(trail, at: datetime, request_ref: str, organizations: tuple[str, ...]):
    return record(
        trail,
        at,
        AuditAction.REQUEST_RECEIVED,
        AuditDomain.SYNCHRONIZATION,
        "clin-x",
        SubjectType.SYNCHRONIZATION_REQUEST,
        request_ref,
        organizations,
    )


def test_record_appends_an_event_with_the_next_reference_and_unique_organizations():
    trail = FakeAuditTrail()

    event = record(
        trail,
        DEMO_NOW,
        AuditAction.AUTHORIZATION_CHECKED,
        AuditDomain.SYNCHRONIZATION,
        "clin-x",
        SubjectType.DECISION,
        "dec-sync-001",
        ("org-governance", "org-hospital-a", "org-hospital-a"),
        AuditOutcome.DENIED,
        "not_found",
    )

    assert event.event_ref == "evt-001"
    assert event.organization_refs == ("org-governance", "org-hospital-a")
    assert trail.events() == [event]


def test_lists_newest_first_then_latest_recorded_at_the_same_time():
    trail = FakeAuditTrail()
    old = received(trail, DEMO_NOW - timedelta(days=1), "sync-001", ("org-hospital-a",))
    first = received(trail, DEMO_NOW, "sync-002", ("org-hospital-b",))
    second = received(trail, DEMO_NOW, "sync-003", ("org-hospital-a",))

    assert list_events(trail, AuditFilter()) == [second, first, old]
    assert list_events(trail, AuditFilter(), limit=1) == [second]


def test_filters_by_organization_subject_domain_and_action():
    trail = FakeAuditTrail()
    a = received(trail, DEMO_NOW, "sync-001", ("org-hospital-a", "org-hospital-b"))
    b = received(trail, DEMO_NOW, "sync-002", ("org-hospital-b",))

    assert list_events(trail, AuditFilter(organization_ref="org-hospital-a")) == [a]
    assert list_events(trail, AuditFilter(subject_ref="sync-002")) == [b]
    assert list_events(trail, AuditFilter(domain=AuditDomain.RESEARCH)) == []
    assert list_events(trail, AuditFilter(action=AuditAction.REQUEST_RECEIVED)) == [
        b,
        a,
    ]


def test_get_event():
    trail = FakeAuditTrail()
    event = received(trail, DEMO_NOW, "sync-001", ("org-hospital-a",))

    assert get_event("evt-001", trail) == event
    with pytest.raises(EventNotFound):
        get_event("evt-404", trail)
