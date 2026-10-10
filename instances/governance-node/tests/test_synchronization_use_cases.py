from dataclasses import replace
from datetime import timedelta

import pytest

from application.synchronization import (
    RequestNotFound,
    check_sync_authorization,
    decide_request,
    get_request,
    list_requests,
    submit_request,
)
from domain.hospital_application import ApplicationStatus, Findings, HospitalApplication
from domain.audit import AuditOutcome
from domain.hospital_approval import Outcome, Reviewer
from domain.synchronization import (
    CheckState,
    Consent,
    ConsentBasis,
    DenialReason,
    ExchangeAsk,
    NotPending,
    RequestStatus,
    ScopeItem,
    SyncDecisionDraft,
    SynchronizationDecision,
)
from tests.conftest import DEMO_NOW
from tests.test_audit_use_cases import FakeAuditTrail
from tests.test_synchronization import GRANT_A, PURPOSE, SYNC_001


class FakeSyncStore:
    """Test double at the SynchronizationStore port."""

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
        request = new_request(f"sync-{len(self.reqs) + 1:03d}")
        self.reqs[request.request_ref] = request
        return request

    def record(self, decided, decision):
        if self.reqs[decided.request_ref].decision_ref:
            raise NotPending("decided in the meantime")
        self.reqs[decided.request_ref] = decided
        self.decs[decision.decision_ref] = decision


class FakeApplications:
    def __init__(self, approved_orgs) -> None:
        self.approved = approved_orgs

    def applications(self):
        return [
            HospitalApplication(
                f"app-{org}",
                org,
                ApplicationStatus.APPROVED,
                DEMO_NOW,
                Findings(),
                f"dec-{org}",
            )
            for org in self.approved
        ]


class FakeGrants:
    def grant(self, ref):
        return {"grant-a-drx": GRANT_A}.get(ref)


class FakeReviewers:
    def reviewer(self, ref):
        return {
            "usr-olfa": Reviewer("usr-olfa", "governance_reviewer", "org-governance")
        }.get(ref)


APPROVED = FakeApplications(["org-hospital-a", "org-hospital-b"])
APPROVE = SyncDecisionDraft(
    Outcome.APPROVED, "Finalité de soins, autorisation active.", (), 13, False
)
ASK = ExchangeAsk(
    "org-hospital-a", "clin-x", "pat-a", frozenset({ScopeItem.MEDICATIONS}), PURPOSE
)


def decided(ref: str, outcome: Outcome, valid_until=None) -> SynchronizationDecision:
    return SynchronizationDecision(
        f"dec-{ref}",
        ref,
        outcome,
        "usr-olfa",
        DEMO_NOW - timedelta(days=200),
        "Motivation de test suffisante.",
        approved_days=10 if outcome is Outcome.APPROVED else None,
        valid_until=valid_until,
    )


def test_lists_by_status_today_then_newest_first():
    older = replace(
        SYNC_001,
        request_ref="sync-010",
        submitted_at=SYNC_001.submitted_at - timedelta(days=3),
    )
    active = replace(SYNC_001, request_ref="sync-011", decision_ref="dec-sync-011")
    expired = replace(SYNC_001, request_ref="sync-012", decision_ref="dec-sync-012")
    rejected = replace(SYNC_001, request_ref="sync-013", decision_ref="dec-sync-013")
    store = FakeSyncStore(
        [rejected, expired, older, active, SYNC_001],
        [
            decided("sync-011", Outcome.APPROVED, DEMO_NOW + timedelta(days=1)),
            decided("sync-012", Outcome.APPROVED, DEMO_NOW),
            decided("sync-013", Outcome.REJECTED),
        ],
    )

    rows = list_requests(store, DEMO_NOW)

    assert [(r.request_ref, s.value) for r, _, s in rows] == [
        ("sync-001", "pending"),
        ("sync-010", "pending"),
        ("sync-011", "active"),
        ("sync-012", "expired"),
        ("sync-013", "rejected"),
    ]
    assert [
        r.request_ref
        for r, _, _ in list_requests(store, DEMO_NOW, RequestStatus.EXPIRED)
    ] == ["sync-012"]


def test_organization_approval_comes_from_hospital_approvals():
    store = FakeSyncStore([SYNC_001])

    def organizations(applications):
        view = get_request(
            "sync-001", store, FakeGrants(), applications, lambda: DEMO_NOW
        )
        return view.checks[0].state

    assert organizations(APPROVED) is CheckState.PASS
    assert organizations(FakeApplications(["org-hospital-a"])) is CheckState.FAIL


def test_submit_then_decide_then_check():
    store = FakeSyncStore()
    audit = FakeAuditTrail()
    request = submit_request(
        "org-hospital-a",
        "clin-x",
        "org-hospital-b",
        "pat-a",
        f"  {PURPOSE} ",
        SYNC_001.scope,
        30,
        Consent(ConsentBasis.PATIENT_GRANT, "grant-a-drx"),
        store,
        audit,
        lambda: DEMO_NOW,
    )
    assert (request.request_ref, request.purpose, request.submitted_at) == (
        "sync-001",
        PURPOSE,
        DEMO_NOW,
    )

    view = get_request("sync-001", store, FakeGrants(), APPROVED, lambda: DEMO_NOW)
    assert (view.status, view.max_approved_days) == (RequestStatus.PENDING, 13)

    decision = decide_request(
        "sync-001",
        "usr-olfa",
        APPROVE,
        store,
        FakeReviewers(),
        FakeGrants(),
        APPROVED,
        audit,
        lambda: DEMO_NOW,
    )
    assert decision.valid_until == DEMO_NOW + timedelta(days=13)

    later = DEMO_NOW + timedelta(minutes=30)
    assert check_sync_authorization(
        "dec-sync-001", ASK, store, audit, lambda: later
    ).authorized
    expired = check_sync_authorization(
        "dec-sync-001", ASK, store, audit, lambda: decision.valid_until
    )
    assert expired.reason is DenialReason.EXPIRED

    rows = [
        (e.action.value, e.subject_ref, e.actor_ref, e.outcome, e.reason, e.recorded_at)
        for e in audit.events()
    ]
    assert rows == [
        ("request_received", "sync-001", "clin-x", None, None, DEMO_NOW),
        (
            "decision_recorded",
            "dec-sync-001",
            "usr-olfa",
            AuditOutcome.APPROVED,
            None,
            DEMO_NOW,
        ),
        (
            "authorization_checked",
            "dec-sync-001",
            ASK.actor_ref,
            AuditOutcome.AUTHORIZED,
            None,
            later,
        ),
        (
            "authorization_checked",
            "dec-sync-001",
            ASK.actor_ref,
            AuditOutcome.DENIED,
            "expired",
            decision.valid_until,
        ),
    ]
    # An authorized check names the target; a denied one only the requester.
    assert [e.organization_refs for e in audit.events()] == [
        ("org-hospital-a", "org-hospital-b"),
        ("org-governance", "org-hospital-a", "org-hospital-b"),
        ("org-governance", "org-hospital-a", "org-hospital-b"),
        ("org-governance", "org-hospital-a"),
    ]
    # No patient reference, purpose, or scope is recorded.
    assert "pat-a" not in repr(audit.events())


def test_unknown_requests_and_decisions():
    store = FakeSyncStore()
    audit = FakeAuditTrail()

    with pytest.raises(RequestNotFound):
        get_request("sync-404", store, FakeGrants(), APPROVED, lambda: DEMO_NOW)
    with pytest.raises(RequestNotFound):
        decide_request(
            "sync-404",
            "usr-olfa",
            APPROVE,
            store,
            FakeReviewers(),
            FakeGrants(),
            APPROVED,
            audit,
            lambda: DEMO_NOW,
        )
    assert (
        check_sync_authorization("dec-x", ASK, store, audit, lambda: DEMO_NOW).reason
        is DenialReason.NOT_FOUND
    )
    # The contract answers a denial, so it is audited.
    [denied] = audit.events()
    assert (denied.subject_ref, denied.reason) == ("dec-x", "not_found")


def test_grant_directory_port_is_used_for_the_consent_check():
    class NoGrants:
        def grant(self, ref):
            return None

    view = get_request(
        "sync-001", FakeSyncStore([SYNC_001]), NoGrants(), APPROVED, lambda: DEMO_NOW
    )

    assert view.checks[1].state is CheckState.FAIL
