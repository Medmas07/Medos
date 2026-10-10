from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from domain.hospital_approval import (
    InvalidDecision,
    Outcome,
    Reviewer,
    ReviewerNotAllowed,
)
from domain.synchronization import (
    CheckState,
    Consent,
    ConsentBasis,
    DenialReason,
    ExchangeAsk,
    InvalidSynchronizationRequest,
    NotPending,
    PatientGrant,
    RequestStatus,
    ReviewContext,
    ScopeItem,
    SyncDecisionDraft,
    SynchronizationRequest,
    check_authorization,
    checks,
    decide,
    max_approved_days,
    status_at,
)
from tests.test_policy import DEMO_POLICY
from tests.conftest import DEMO_NOW

MEDS_LABS = frozenset({ScopeItem.MEDICATIONS, ScopeItem.LAB_REPORTS})
PURPOSE = "Continuité des soins : consultation de cardiologie"
SYNC_001 = SynchronizationRequest(
    request_ref="sync-001",
    requester_organization_ref="org-hospital-a",
    target_organization_ref="org-hospital-b",
    patient_ref="pat-a",
    purpose=PURPOSE,
    scope=MEDS_LABS,
    duration_days=30,
    consent=Consent(ConsentBasis.PATIENT_GRANT, "grant-a-drx"),
    submitted_at=datetime.fromisoformat("2026-10-10T09:05:00+01:00"),
)
GRANT_A = PatientGrant(
    "grant-a-drx",
    "pat-a",
    frozenset(ScopeItem),
    datetime.fromisoformat("2026-10-24T09:00:00+01:00"),
)
APPROVED_ORGS = frozenset({"org-hospital-a", "org-hospital-b", "org-private-practice"})
CONTEXT = ReviewContext(APPROVED_ORGS, GRANT_A, DEMO_NOW, DEMO_POLICY)
OLFA = Reviewer("usr-olfa", "governance_reviewer", "org-governance")
APPROVE_13 = SyncDecisionDraft(
    Outcome.APPROVED, "Finalité de soins, autorisation active.", (), 13, False
)
REJECT = SyncDecisionDraft(
    Outcome.REJECTED, "Finalité non compatible avec les soins.", (), None, False
)


def check_states(request=SYNC_001, context=CONTEXT) -> dict:
    return {c.check: (c.state, c.detail) for c in checks(request, context)}


def issues(draft, request=SYNC_001, context=CONTEXT) -> list[str]:
    with pytest.raises(InvalidDecision) as raised:
        decide(request, None, OLFA, draft, context)
    return [i.field for i in raised.value.issues]


def test_patient_a_grant_caps_the_approval_at_13_days():
    assert max_approved_days(SYNC_001, CONTEXT) == 13
    states = check_states()
    assert {k: s for k, (s, _) in states.items()} == {
        "organizations": CheckState.PASS,
        "consent": CheckState.PASS,
        "duration": CheckState.PASS,
    }
    assert states["duration"][1] == (
        "30 days requested, limited to 13 days by the end of the patient grant."
    )


def test_without_a_grant_the_requested_duration_applies():
    signed = replace(SYNC_001, consent=Consent(ConsentBasis.SIGNED_CONSENT_FORM))

    assert max_approved_days(signed, replace(CONTEXT, grant=None)) == 30


@pytest.mark.parametrize(
    "grant, message",
    [
        (None, "Grant grant-a-drx is unknown to the Governance Node."),
        (replace(GRANT_A, revoked=True), "Grant grant-a-drx was revoked."),
        (
            replace(GRANT_A, expires_at=DEMO_NOW - timedelta(days=1)),
            "Grant grant-a-drx expired on 2026-10-09T10:00:00+01:00.",
        ),
        (
            replace(GRANT_A, patient_ref="pat-b"),
            "Grant grant-a-drx concerns another patient.",
        ),
        (
            replace(GRANT_A, scope=frozenset({ScopeItem.MEDICATIONS})),
            "Grant grant-a-drx does not cover: lab_reports.",
        ),
    ],
)
def test_each_grant_problem_fails_the_consent_check(grant, message):
    state, detail = check_states(context=replace(CONTEXT, grant=grant))["consent"]

    assert (state, detail) == (CheckState.FAIL, message)


@pytest.mark.parametrize(
    "basis, state",
    [
        (ConsentBasis.NONE, CheckState.FAIL),
        (ConsentBasis.SIGNED_CONSENT_FORM, CheckState.MANUAL),
        (ConsentBasis.EMERGENCY_OVERRIDE, CheckState.MANUAL),
    ],
)
def test_other_consent_bases(basis, state):
    request = replace(SYNC_001, consent=Consent(basis))

    assert check_states(request, replace(CONTEXT, grant=None))["consent"][0] is state


def test_an_unapproved_organization_fails():
    # Hospital C is still in onboarding.
    request = replace(SYNC_001, target_organization_ref="org-hospital-c")

    assert check_states(request)["organizations"][0] is CheckState.FAIL


def test_a_grant_ending_within_a_day_leaves_no_duration():
    context = replace(
        CONTEXT, grant=replace(GRANT_A, expires_at=DEMO_NOW + timedelta(hours=5))
    )

    assert max_approved_days(SYNC_001, context) == 0
    assert check_states(context=context)["duration"] == (
        CheckState.FAIL,
        "No duration is possible before the patient grant ends.",
    )


def test_approval_is_a_temporary_authorization():
    decision, decided = decide(SYNC_001, None, OLFA, APPROVE_13, CONTEXT)

    assert decision.decision_ref == "dec-sync-001"
    assert decision.approved_days == 13
    assert decision.valid_until == DEMO_NOW + timedelta(days=13)
    assert decided.decision_ref == "dec-sync-001"
    assert status_at(decided, decision, DEMO_NOW) is RequestStatus.ACTIVE
    assert status_at(decided, decision, decision.valid_until) is RequestStatus.EXPIRED


def test_rejection_is_always_possible_even_when_checks_fail():
    context = ReviewContext(frozenset(), None, DEMO_NOW, DEMO_POLICY)

    decision, _ = decide(SYNC_001, None, OLFA, REJECT, context)

    assert (decision.outcome, decision.valid_until) == (Outcome.REJECTED, None)
    assert status_at(SYNC_001, decision, DEMO_NOW) is RequestStatus.REJECTED


def test_approval_beyond_the_grant_is_refused():
    assert issues(replace(APPROVE_13, approved_days=30)) == ["approved_days"]
    assert issues(replace(APPROVE_13, approved_days=0)) == ["approved_days"]
    assert issues(replace(APPROVE_13, approved_days=None)) == ["approved_days"]


def test_approval_while_a_check_fails_is_refused():
    context = replace(CONTEXT, grant=replace(GRANT_A, revoked=True))

    assert issues(APPROVE_13, context=context) == ["checks"]


def test_manual_checks_must_be_confirmed():
    signed = replace(SYNC_001, consent=Consent(ConsentBasis.SIGNED_CONSENT_FORM))
    context = replace(CONTEXT, grant=None)

    assert issues(APPROVE_13, signed, context) == ["manual_checks_confirmed"]
    decide(
        signed, None, OLFA, replace(APPROVE_13, manual_checks_confirmed=True), context
    )


def test_rejection_has_neither_conditions_nor_duration():
    assert issues(
        replace(REJECT, conditions=("x",), approved_days=3, rationale="court")
    ) == [
        "rationale",
        "conditions",
        "approved_days",
    ]


@pytest.mark.parametrize(
    "reviewer",
    [
        None,
        Reviewer("clin-x", "physician", "org-hospital-a"),
        Reviewer("usr-a", "governance_reviewer", "org-hospital-a"),
        Reviewer("usr-b", "governance_reviewer", "org-hospital-b"),
    ],
)
def test_only_an_uninvolved_governance_reviewer_decides(reviewer):
    with pytest.raises(ReviewerNotAllowed):
        decide(SYNC_001, None, reviewer, APPROVE_13, CONTEXT)


def test_a_decided_request_is_not_pending():
    decision, decided = decide(SYNC_001, None, OLFA, APPROVE_13, CONTEXT)

    with pytest.raises(NotPending, match="sync-001 is approved"):
        decide(decided, decision, OLFA, REJECT, CONTEXT)


@pytest.mark.parametrize(
    "changes",
    [
        {"request_ref": "001"},
        {"target_organization_ref": "org-hospital-a"},
        {"patient_ref": "Leïla Mansouri"},
        {"purpose": "  "},
        {"scope": frozenset()},
        {"duration_days": 0},
        {"duration_days": 366},
        {"submitted_at": datetime(2026, 10, 10, 9, 5)},
    ],
)
def test_request_invariants(changes):
    with pytest.raises(InvalidSynchronizationRequest):
        replace(SYNC_001, **changes)


@pytest.mark.parametrize(
    "basis, grant_ref",
    [(ConsentBasis.PATIENT_GRANT, None), (ConsentBasis.NONE, "grant-a-drx")],
)
def test_a_grant_is_named_for_a_patient_grant_basis_only(basis, grant_ref):
    with pytest.raises(InvalidSynchronizationRequest):
        Consent(basis, grant_ref)


ASK = ExchangeAsk(
    "org-hospital-a", "clin-x", "pat-a", frozenset({ScopeItem.MEDICATIONS}), PURPOSE
)


def approved_sync_001():
    decision, decided = decide(SYNC_001, None, OLFA, APPROVE_13, CONTEXT)
    return decision, decided


def test_an_approved_decision_authorizes_the_exact_exchange():
    result = check_authorization("dec-sync-001", approved_sync_001(), ASK, DEMO_NOW)

    assert result.authorized
    assert result.target_organization_refs == ("org-hospital-b",)
    assert result.scope == MEDS_LABS
    assert result.purpose == PURPOSE
    assert result.valid_until == DEMO_NOW + timedelta(days=13)


@pytest.mark.parametrize(
    "ask_changes, at, reason",
    [
        ({}, DEMO_NOW - timedelta(seconds=1), DenialReason.NOT_YET_VALID),
        ({}, DEMO_NOW + timedelta(days=13), DenialReason.EXPIRED),
        (
            {"requester_organization_ref": "org-hospital-c"},
            DEMO_NOW,
            DenialReason.REQUESTER_MISMATCH,
        ),
        ({"patient_ref": "pat-b"}, DEMO_NOW, DenialReason.PATIENT_MISMATCH),
        ({"scope": frozenset(ScopeItem)}, DEMO_NOW, DenialReason.SCOPE_EXCEEDED),
        ({"purpose": "Recherche"}, DEMO_NOW, DenialReason.PURPOSE_MISMATCH),
        # The first failing reason wins.
        (
            {"patient_ref": "pat-b", "purpose": "Recherche"},
            DEMO_NOW,
            DenialReason.PATIENT_MISMATCH,
        ),
    ],
)
def test_each_difference_denies(ask_changes, at, reason):
    result = check_authorization(
        "dec-sync-001", approved_sync_001(), replace(ASK, **ask_changes), at
    )

    assert result.reason is reason
    assert (result.target_organization_refs, result.scope, result.purpose) == (
        (),
        frozenset(),
        None,
    )
    assert result.valid_until == DEMO_NOW + timedelta(days=13)


def test_unknown_and_rejected_decisions_deny():
    decision, decided = decide(SYNC_001, None, OLFA, REJECT, CONTEXT)

    assert (
        check_authorization("dec-x", None, ASK, DEMO_NOW).reason
        is DenialReason.NOT_FOUND
    )
    rejected = check_authorization("dec-sync-001", (decision, decided), ASK, DEMO_NOW)
    assert (rejected.reason, rejected.valid_until) == (DenialReason.NOT_APPROVED, None)
