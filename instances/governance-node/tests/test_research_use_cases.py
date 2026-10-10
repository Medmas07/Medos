from dataclasses import replace
from datetime import timedelta

import pytest

from application.research import (
    DecisionNotFound,
    RequestNotFound,
    check_research_authorization,
    decide_request,
    get_request,
    list_requests,
    submit_request,
)
from domain.audit import AuditOutcome
from domain.hospital_approval import Outcome, Reviewer
from domain.research import (
    CheckState,
    DenialReason,
    NotUnderReview,
    RequestStatus,
    ResearchDecision,
)
from tests.test_policy import DEMO_POLICIES
from tests.conftest import DEMO_NOW
from tests.test_audit_use_cases import FakeAuditTrail
from tests.test_research import APPROVE, JOB_001, RAR
from tests.test_synchronization_use_cases import FakeApplications


class FakeResearchStore:
    """Test double at the ResearchStore port."""

    def __init__(self, requests=(), decisions=()) -> None:
        self.reqs = {r.request_ref: r for r in requests}
        self.decs = {d.decision_ref: d for d in decisions}

    def requests(self):
        return list(self.reqs.values())

    def request(self, ref):
        return self.reqs.get(ref)

    def decision(self, ref):
        return self.decs.get(ref)

    def submit(self, new_request):
        request = new_request(f"rar-{len(self.reqs) + 1:03d}")
        self.reqs[request.request_ref] = request
        return request

    def record(self, decided, decision):
        if self.reqs[decided.request_ref].decision_ref:
            raise NotUnderReview("decided in the meantime")
        self.reqs[decided.request_ref] = decided
        self.decs[decision.decision_ref] = decision


class FakeReviewers:
    def reviewer(self, ref):
        return {
            "usr-olfa": Reviewer("usr-olfa", "governance_reviewer", "org-governance")
        }.get(ref)


APPROVED = FakeApplications(["org-hospital-a", "org-hospital-b"])
PENDING = replace(RAR, decision_ref=None)


def decided(ref: str, outcome: Outcome, valid_until=None) -> ResearchDecision:
    approved = outcome is Outcome.APPROVED
    return ResearchDecision(
        f"dec-{ref}",
        ref,
        outcome,
        "usr-olfa",
        DEMO_NOW - timedelta(days=400),
        "Motivation de test suffisante.",
        approved_organization_refs=("org-hospital-a",) if approved else (),
        approved_variables=("hba1c",) if approved else (),
        minimum_cell_size=10 if approved else None,
        valid_until=valid_until,
    )


def test_lists_under_review_first_then_by_status_today():
    store = FakeResearchStore(
        [
            replace(RAR, request_ref="rar-013", decision_ref="dec-rar-013"),
            replace(RAR, request_ref="rar-012", decision_ref="dec-rar-012"),
            replace(RAR, request_ref="rar-011", decision_ref="dec-rar-011"),
            replace(PENDING, request_ref="rar-010"),
        ],
        [
            decided("rar-011", Outcome.APPROVED, DEMO_NOW + timedelta(days=1)),
            decided("rar-012", Outcome.APPROVED, DEMO_NOW),
            decided("rar-013", Outcome.REJECTED),
        ],
    )

    rows = list_requests(store, DEMO_NOW)

    assert [(r.request_ref, s.value) for r, _, s in rows] == [
        ("rar-010", "under_review"),
        ("rar-011", "authorized"),
        ("rar-012", "expired"),
        ("rar-013", "rejected"),
    ]
    assert [
        r.request_ref
        for r, _, _ in list_requests(store, DEMO_NOW, RequestStatus.EXPIRED)
    ] == ["rar-012"]


def test_eligibility_comes_from_hospital_approvals():
    view = get_request(
        "rar-001", FakeResearchStore([PENDING]), APPROVED, lambda: DEMO_NOW
    )

    assert view.eligible_organization_refs == ("org-hospital-a", "org-hospital-b")
    none = get_request(
        "rar-001", FakeResearchStore([PENDING]), FakeApplications([]), lambda: DEMO_NOW
    )
    assert none.checks[1].state is CheckState.FAIL


def test_submit_decide_then_check():
    store = FakeResearchStore()
    audit = FakeAuditTrail()
    request = submit_request(
        lambda ref, now: replace(PENDING, request_ref=ref, submitted_at=now),
        store,
        audit,
        lambda: DEMO_NOW,
    )
    assert (request.request_ref, request.submitted_at) == ("rar-001", DEMO_NOW)

    decision = decide_request(
        "rar-001",
        "usr-olfa",
        APPROVE,
        store,
        FakeReviewers(),
        APPROVED,
        DEMO_POLICIES,
        audit,
        lambda: DEMO_NOW,
    )

    assert check_research_authorization(
        decision.decision_ref, JOB_001, store, audit, lambda: DEMO_NOW
    ).approved
    later = check_research_authorization(
        decision.decision_ref, JOB_001, store, audit, lambda: decision.valid_until
    )
    assert later.reason is DenialReason.EXPIRED

    rows = [
        (e.action.value, e.subject_ref, e.actor_ref, e.outcome, e.reason)
        for e in audit.events()
    ]
    assert rows == [
        ("request_received", "rar-001", PENDING.submitted_by_ref, None, None),
        ("decision_recorded", "dec-rar-001", "usr-olfa", AuditOutcome.APPROVED, None),
        (
            "authorization_checked",
            "dec-rar-001",
            JOB_001.requested_by,
            AuditOutcome.AUTHORIZED,
            None,
        ),
        (
            "authorization_checked",
            "dec-rar-001",
            JOB_001.requested_by,
            AuditOutcome.DENIED,
            "expired",
        ),
    ]
    assert audit.events()[1].organization_refs == (
        "org-governance",
        PENDING.research_organization_ref,
        *PENDING.participating_organization_refs,
    )
    assert audit.events()[2].organization_refs == (
        "org-governance",
        *sorted(JOB_001.target_organization_refs),
    )


def test_unknown_requests_and_decisions():
    store = FakeResearchStore()
    audit = FakeAuditTrail()

    with pytest.raises(RequestNotFound):
        get_request("rar-404", store, APPROVED, lambda: DEMO_NOW)
    with pytest.raises(RequestNotFound):
        decide_request(
            "rar-404",
            "usr-olfa",
            APPROVE,
            store,
            FakeReviewers(),
            APPROVED,
            DEMO_POLICIES,
            audit,
            lambda: DEMO_NOW,
        )
    with pytest.raises(DecisionNotFound):
        check_research_authorization(
            "dec-rar-404", JOB_001, store, audit, lambda: DEMO_NOW
        )
    # An unknown decision is a 404, not an answer: nothing is audited.
    assert audit.events() == []
