from dataclasses import replace
from datetime import timedelta

import pytest

from application.synchronization import (
    GrantsUnavailable,
    RequestNotFound,
    check_sync_authorization,
    decide_request,
    get_request,
    list_requests,
    submit_request,
)
from domain.hospital_application import ApplicationStatus, Findings, HospitalApplication
from domain.audit import AuditOutcome
from domain.hospital_approval import InvalidDecision, Outcome, Reviewer
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
from tests.test_policy import DEMO_POLICIES
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
    """Test double at the PatientGrantDirectory port: what Hospital B holds."""

    mode = "fake"

    def __init__(self, grants=(GRANT_A,), holder="org-hospital-b") -> None:
        self.grants = {g.grant_ref: g for g in grants}
        self.holder = holder
        self.asked = []

    def grant(self, holder_organization_ref, patient_ref, grant_ref):
        self.asked.append((holder_organization_ref, patient_ref, grant_ref))
        grant = self.grants.get(grant_ref)
        if holder_organization_ref != self.holder or grant is None:
            return None
        return grant if grant.patient_ref == patient_ref else None


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
            "sync-001",
            store,
            FakeGrants(),
            applications,
            DEMO_POLICIES,
            lambda: DEMO_NOW,
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

    view = get_request(
        "sync-001", store, FakeGrants(), APPROVED, DEMO_POLICIES, lambda: DEMO_NOW
    )
    assert (view.status, view.max_approved_days) == (RequestStatus.PENDING, 13)

    decision = decide_request(
        "sync-001",
        "usr-olfa",
        APPROVE,
        store,
        FakeReviewers(),
        FakeGrants(),
        APPROVED,
        DEMO_POLICIES,
        audit,
        lambda: DEMO_NOW,
    )
    assert decision.valid_until == DEMO_NOW + timedelta(days=13)

    later = DEMO_NOW + timedelta(minutes=30)
    assert check_sync_authorization(
        "dec-sync-001", ASK, store, FakeGrants(), audit, lambda: later
    ).authorized
    expired = check_sync_authorization(
        "dec-sync-001", ASK, store, FakeGrants(), audit, lambda: decision.valid_until
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
        get_request(
            "sync-404", store, FakeGrants(), APPROVED, DEMO_POLICIES, lambda: DEMO_NOW
        )
    with pytest.raises(RequestNotFound):
        decide_request(
            "sync-404",
            "usr-olfa",
            APPROVE,
            store,
            FakeReviewers(),
            FakeGrants(),
            APPROVED,
            DEMO_POLICIES,
            audit,
            lambda: DEMO_NOW,
        )
    assert (
        check_sync_authorization(
            "dec-x", ASK, store, FakeGrants(), audit, lambda: DEMO_NOW
        ).reason
        is DenialReason.NOT_FOUND
    )
    # The contract answers a denial, so it is audited.
    [denied] = audit.events()
    assert (denied.subject_ref, denied.reason) == ("dec-x", "not_found")


def test_grant_directory_port_is_used_for_the_consent_check():
    class NoGrants:
        mode = "fake"

        def grant(self, holder_organization_ref, patient_ref, grant_ref):
            return None

    view = get_request(
        "sync-001",
        FakeSyncStore([SYNC_001]),
        NoGrants(),
        APPROVED,
        DEMO_POLICIES,
        lambda: DEMO_NOW,
    )

    assert view.checks[1].state is CheckState.FAIL


class UnreachableGrants:
    mode = "fake"

    def grant(self, holder_organization_ref, patient_ref, grant_ref):
        raise GrantsUnavailable(
            f"the Hospital Node of {holder_organization_ref} could not be reached."
        )


def approved_sync_001(audit) -> FakeSyncStore:
    store = FakeSyncStore([SYNC_001])
    decide_request(
        "sync-001",
        "usr-olfa",
        APPROVE,
        store,
        FakeReviewers(),
        FakeGrants(),
        APPROVED,
        DEMO_POLICIES,
        audit,
        lambda: DEMO_NOW,
    )
    return store


def test_consent_is_asked_of_the_target_organizations_node():
    grants = FakeGrants()

    get_request(
        "sync-001",
        FakeSyncStore([SYNC_001]),
        grants,
        APPROVED,
        DEMO_POLICIES,
        lambda: DEMO_NOW,
    )

    assert grants.asked == [("org-hospital-b", "pat-a", "grant-a-drx")]
    held_elsewhere = FakeGrants(holder="org-hospital-a")
    view = get_request(
        "sync-001",
        FakeSyncStore([SYNC_001]),
        held_elsewhere,
        APPROVED,
        DEMO_POLICIES,
        lambda: DEMO_NOW,
    )
    assert view.checks[1].state is CheckState.FAIL


def test_an_unreachable_holder_makes_approval_impossible():
    view = get_request(
        "sync-001",
        FakeSyncStore([SYNC_001]),
        UnreachableGrants(),
        APPROVED,
        DEMO_POLICIES,
        lambda: DEMO_NOW,
    )

    assert view.checks[1].state is CheckState.FAIL
    with pytest.raises(InvalidDecision):
        decide_request(
            "sync-001",
            "usr-olfa",
            APPROVE,
            FakeSyncStore([SYNC_001]),
            FakeReviewers(),
            UnreachableGrants(),
            APPROVED,
            DEMO_POLICIES,
            FakeAuditTrail(),
            lambda: DEMO_NOW,
        )


def test_a_grant_revoked_at_the_holder_stops_an_approved_synchronization():
    audit = FakeAuditTrail()
    store = approved_sync_001(audit)
    revoked = FakeGrants([replace(GRANT_A, revoked=True)])

    result = check_sync_authorization(
        "dec-sync-001", ASK, store, revoked, audit, lambda: DEMO_NOW
    )

    assert result.reason is DenialReason.REVOKED
    event = audit.events()[-1]
    assert (event.outcome, event.reason, event.organization_refs) == (
        AuditOutcome.DENIED,
        "revoked",
        ("org-governance", "org-hospital-a"),
    )


def test_an_unreachable_holder_authorizes_nothing_and_is_audited():
    audit = FakeAuditTrail()
    store = approved_sync_001(audit)

    with pytest.raises(GrantsUnavailable):
        check_sync_authorization(
            "dec-sync-001", ASK, store, UnreachableGrants(), audit, lambda: DEMO_NOW
        )

    event = audit.events()[-1]
    assert (event.outcome, event.reason) == (AuditOutcome.DENIED, "consent_unavailable")


def test_a_denial_before_consent_does_not_ask_the_holder():
    grants = FakeGrants()

    check_sync_authorization(
        "dec-x", ASK, FakeSyncStore(), grants, FakeAuditTrail(), lambda: DEMO_NOW
    )

    assert grants.asked == []
