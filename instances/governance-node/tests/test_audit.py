from dataclasses import replace
from datetime import datetime

import pytest

from domain.audit import (
    AuditAction,
    AuditDomain,
    AuditEvent,
    AuditFilter,
    AuditOutcome,
    InvalidAuditEvent,
    SubjectType,
)
from tests.conftest import DEMO_NOW

DECISION = AuditEvent(
    event_ref="evt-001",
    recorded_at=DEMO_NOW,
    action=AuditAction.DECISION_RECORDED,
    domain=AuditDomain.SYNCHRONIZATION,
    actor_ref="usr-olfa",
    subject_type=SubjectType.DECISION,
    subject_ref="dec-sync-001",
    outcome=AuditOutcome.APPROVED,
    reason=None,
    organization_refs=("org-governance", "org-hospital-a", "org-hospital-b"),
)
DENIED = replace(
    DECISION,
    action=AuditAction.AUTHORIZATION_CHECKED,
    actor_ref="clin-x",
    outcome=AuditOutcome.DENIED,
    reason="expired",
)


def test_valid_events():
    assert DENIED.reason == "expired"
    received = replace(
        DECISION,
        action=AuditAction.REQUEST_RECEIVED,
        actor_ref=None,
        subject_type=SubjectType.SYNCHRONIZATION_REQUEST,
        subject_ref="sync-001",
        outcome=None,
    )
    assert received.actor_ref is None


@pytest.mark.parametrize(
    "changes",
    [
        {"event_ref": "sync-001"},
        {"recorded_at": datetime(2026, 10, 10, 10)},
        {"organization_refs": ()},
        {"organization_refs": ("org-a", "org-a")},
        {"actor_ref": ""},
        {"actor_ref": "x" * 129},
        {"subject_ref": "dec\n1"},
        # A decision is approved or rejected; a request has no outcome.
        {"outcome": AuditOutcome.AUTHORIZED},
        {"outcome": None},
        {"subject_type": SubjectType.SYNCHRONIZATION_REQUEST},
        {"action": AuditAction.REQUEST_RECEIVED},
        # A reason only for a denied check.
        {"reason": "expired"},
    ],
)
def test_invalid_events(changes):
    with pytest.raises(InvalidAuditEvent):
        replace(DECISION, **changes)


@pytest.mark.parametrize("reason", [None, "Expired", "expired; drop"])
def test_a_denied_check_needs_a_reason_code(reason):
    with pytest.raises(InvalidAuditEvent):
        replace(DENIED, reason=reason)


def test_filter():
    assert AuditFilter().matches(DECISION)
    assert AuditFilter(organization_ref="org-hospital-b").matches(DECISION)
    assert not AuditFilter(organization_ref="org-research-lab").matches(DECISION)
    assert not AuditFilter(domain=AuditDomain.RESEARCH).matches(DECISION)
    assert not AuditFilter(action=AuditAction.AUTHORIZATION_CHECKED).matches(DECISION)
    assert AuditFilter(
        subject_ref="dec-sync-001", action=AuditAction.AUTHORIZATION_CHECKED
    ).matches(DENIED)
