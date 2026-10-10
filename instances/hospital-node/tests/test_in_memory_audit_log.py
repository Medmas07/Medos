from datetime import timedelta

import pytest

from adapters.outbound.in_memory_audit_log import InMemoryAuditLog
from domain.audit_event import AuditEvent, AuditOutcome, AuditQuery, InvalidAuditQuery
from domain.patient_history import (
    Authorization,
    AuthorizationBasis,
    HistoryQuery,
    Requester,
    ScopeItem,
)
from tests.conftest import DEMO_NOW


def event(n: int, patient_ref: str = "pat-a", outcome=AuditOutcome.DISCLOSED):
    query = HistoryQuery(
        query_id=f"00000000-0000-4000-8000-{n:012d}",
        patient_ref=patient_ref,
        scope=frozenset({ScopeItem.MEDICATIONS}),
        purpose="Consultation",
        requested_by=Requester("org-hospital-a", "clin-x"),
        authorization=Authorization(
            AuthorizationBasis.PATIENT_ACCESS_GRANT, "grant-a-drx", DEMO_NOW
        ),
    )
    return AuditEvent.of_query(
        f"evt-{n}", DEMO_NOW + timedelta(seconds=n), query, outcome
    )


def log_with(*events) -> InMemoryAuditLog:
    log = InMemoryAuditLog()
    for e in events:
        log.record(e)
    return log


def ids(events) -> list[str]:
    return [e.event_id for e in events]


def test_starts_empty_and_is_not_durable():
    log = InMemoryAuditLog()

    assert log.events(AuditQuery()) == ()
    assert log.durable is False


def test_lists_newest_first():
    log = log_with(event(1), event(2), event(3))

    assert ids(log.events(AuditQuery())) == ["evt-3", "evt-2", "evt-1"]


def test_filters_by_patient_query_and_outcome():
    log = log_with(
        event(1),
        event(2, patient_ref="pat-b"),
        event(3, outcome=AuditOutcome.DENIED),
    )

    assert ids(log.events(AuditQuery(patient_ref="pat-b"))) == ["evt-2"]
    assert ids(log.events(AuditQuery(outcome=AuditOutcome.DENIED))) == ["evt-3"]
    assert ids(log.events(AuditQuery(query_id=event(1).query_id))) == ["evt-1"]


def test_limit_keeps_the_newest_matches():
    log = log_with(event(1), event(2), event(3))

    assert ids(log.events(AuditQuery(limit=2))) == ["evt-3", "evt-2"]


def test_listing_does_not_change_the_trail():
    log = log_with(event(1))
    listed = log.events(AuditQuery())

    assert isinstance(listed, tuple)
    assert ids(log.events(AuditQuery())) == ["evt-1"]


@pytest.mark.parametrize("limit", [0, 501])
def test_rejects_a_limit_out_of_range(limit):
    with pytest.raises(InvalidAuditQuery):
        AuditQuery(limit=limit)
