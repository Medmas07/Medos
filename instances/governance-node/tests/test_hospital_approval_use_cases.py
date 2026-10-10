from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from domain.audit import AuditAction
from application.hospital_approval import (
    ApplicationNotFound,
    decide_application,
    get_application,
    get_hospital_approval,
    list_applications,
)
from domain.hospital_application import ApplicationStatus, Findings, HospitalApplication
from domain.hospital_approval import (
    DecisionDraft,
    HospitalApprovalDecision,
    NotAwaitingReview,
    Outcome,
    Reviewer,
)
from tests.test_policy import DEMO_POLICIES
from tests.conftest import DEMO_NOW
from tests.test_audit_use_cases import FakeAuditTrail

T0 = datetime.fromisoformat("2026-01-01T09:00:00+01:00")


def application(ref: str, status: ApplicationStatus, days: int) -> HospitalApplication:
    decided = status in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED)
    return HospitalApplication(
        f"app-{ref}",
        f"org-{ref}",
        status,
        T0 + timedelta(days=days),
        Findings(),
        f"dec-{ref}" if decided else None,
    )


class FakeStore:
    """Test double at the HospitalApplicationStore port."""

    def __init__(self, applications, decisions=()) -> None:
        self.apps = {a.application_ref: a for a in applications}
        self.decisions = {d.decision_ref: d for d in decisions}

    def applications(self):
        return list(self.apps.values())

    def application(self, ref):
        return self.apps.get(ref)

    def decision(self, ref):
        return self.decisions.get(ref)

    def record(self, decided, decision):
        if not self.apps[decided.application_ref].awaiting_review:
            raise NotAwaitingReview("decided in the meantime")
        self.apps[decided.application_ref] = decided
        self.decisions[decision.decision_ref] = decision


class FakeReviewers:
    def reviewer(self, ref):
        return {"usr-olfa": Reviewer("usr-olfa", "governance_reviewer", "org-gov")}.get(
            ref
        )


APPROVE = DecisionDraft(Outcome.APPROVED, "Dossier complet et conforme.", (), True)
STORE_APPS = [
    application("old-approved", ApplicationStatus.APPROVED, 0),
    application("new-approved", ApplicationStatus.APPROVED, 5),
    application("rejected", ApplicationStatus.REJECTED, 9),
    application("pending", ApplicationStatus.PENDING, 8),
    application("review-old", ApplicationStatus.HUMAN_REVIEW, 1),
    application("review-new", ApplicationStatus.HUMAN_REVIEW, 7),
]


def test_lists_review_first_then_pending_then_decided_newest_first():
    refs = [a.application_ref for a in list_applications(FakeStore(STORE_APPS))]

    assert refs == [
        "app-review-new",
        "app-review-old",
        "app-pending",
        "app-new-approved",
        "app-old-approved",
        "app-rejected",
    ]


def test_filters_by_status_and_can_be_empty():
    store = FakeStore(STORE_APPS)

    assert [
        a.application_ref
        for a in list_applications(store, ApplicationStatus.HUMAN_REVIEW)
    ] == ["app-review-new", "app-review-old"]
    assert list_applications(FakeStore([]), ApplicationStatus.PENDING) == []


def test_decides_and_stores_the_decision_at_the_clock_time():
    store = FakeStore(STORE_APPS)
    audit = FakeAuditTrail()

    decision = decide_application(
        "app-review-old",
        "usr-olfa",
        APPROVE,
        store,
        FakeReviewers(),
        DEMO_POLICIES,
        audit,
        lambda: DEMO_NOW,
    )

    assert decision.decided_at == DEMO_NOW
    application_now, stored = get_application("app-review-old", store)
    assert application_now.status is ApplicationStatus.APPROVED
    assert stored == decision
    assert get_hospital_approval("dec-review-old", store) == decision
    [event] = audit.events()
    assert (event.action, event.subject_ref, event.outcome.value) == (
        AuditAction.DECISION_RECORDED,
        "dec-review-old",
        "approved",
    )
    assert (event.actor_ref, event.recorded_at) == ("usr-olfa", DEMO_NOW)
    assert event.organization_refs == ("org-governance", "org-review-old")


def test_a_second_decision_is_refused():
    store = FakeStore(STORE_APPS)
    audit = FakeAuditTrail()
    decide_application(
        "app-review-old",
        "usr-olfa",
        APPROVE,
        store,
        FakeReviewers(),
        DEMO_POLICIES,
        audit,
        lambda: DEMO_NOW,
    )

    with pytest.raises(NotAwaitingReview):
        decide_application(
            "app-review-old",
            "usr-olfa",
            replace(APPROVE, outcome=Outcome.REJECTED),
            store,
            FakeReviewers(),
            DEMO_POLICIES,
            audit,
            lambda: DEMO_NOW,
        )
    # A refused decision is not audited.
    assert len(audit.events()) == 1


def test_unknown_application():
    with pytest.raises(ApplicationNotFound):
        get_application("app-unknown", FakeStore(STORE_APPS))
    with pytest.raises(ApplicationNotFound):
        decide_application(
            "app-unknown",
            "usr-olfa",
            APPROVE,
            FakeStore([]),
            FakeReviewers(),
            DEMO_POLICIES,
            FakeAuditTrail(),
            lambda: DEMO_NOW,
        )


def test_get_application_returns_its_decision():
    decision = HospitalApprovalDecision(
        "dec-new-approved",
        "app-new-approved",
        "org-new-approved",
        Outcome.APPROVED,
        "usr-olfa",
        T0,
        "Dossier complet et conforme.",
    )

    _, found = get_application("app-new-approved", FakeStore(STORE_APPS, [decision]))

    assert found == decision
