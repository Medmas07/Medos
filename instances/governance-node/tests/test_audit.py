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


SIGNED_IN = AuditEvent(
    event_ref="evt-010",
    recorded_at=DEMO_NOW,
    action=AuditAction.SIGNED_IN,
    domain=AuditDomain.SECURITY,
    actor_ref="usr-olfa",
    subject_type=SubjectType.PERSON,
    subject_ref="usr-olfa",
    outcome=None,
    reason=None,
    organization_refs=("org-governance",),
)
ACCESS_DENIED = replace(
    SIGNED_IN,
    action=AuditAction.ACCESS_DENIED,
    actor_ref="usr-aymen",
    subject_type=SubjectType.PERMISSION,
    subject_ref="governance:audit",
    outcome=AuditOutcome.DENIED,
    reason="permission_denied",
)


def test_valid_security_events():
    refused = replace(
        SIGNED_IN,
        action=AuditAction.SIGN_IN_REFUSED,
        outcome=AuditOutcome.DENIED,
        reason="account_locked",
    )
    assert refused.reason == "account_locked"
    assert ACCESS_DENIED.subject_ref == "governance:audit"


@pytest.mark.parametrize(
    ("event", "changes"),
    [
        # Security actions belong to the security domain, and only they do.
        (SIGNED_IN, {"domain": AuditDomain.SYNCHRONIZATION}),
        (DECISION, {"domain": AuditDomain.SECURITY}),
        # A sign-in concerns a person; a denial a permission, with its reason.
        (SIGNED_IN, {"subject_type": SubjectType.DECISION}),
        (SIGNED_IN, {"outcome": AuditOutcome.DENIED, "reason": "x"}),
        (ACCESS_DENIED, {"subject_type": SubjectType.PERSON}),
        (ACCESS_DENIED, {"reason": None}),
        (ACCESS_DENIED, {"outcome": AuditOutcome.REJECTED}),
    ],
)
def test_invalid_security_events(event, changes):
    with pytest.raises(InvalidAuditEvent):
        replace(event, **changes)


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
