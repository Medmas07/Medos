from dataclasses import replace
from datetime import datetime

import pytest

from domain.hospital_application import (
    ApplicationStatus,
    Findings,
    HospitalApplication,
    InvalidHospitalApplication,
    MissingDocument,
)
from domain.hospital_approval import (
    DecisionDraft,
    InvalidDecision,
    NotAwaitingReview,
    Outcome,
    Reviewer,
    ReviewerNotAllowed,
    decide,
)
from tests.test_policy import DEMO_POLICY
from tests.conftest import DEMO_NOW

SUBMITTED = datetime.fromisoformat("2026-10-06T15:20:00+01:00")
OLFA = Reviewer("usr-olfa", "governance_reviewer", "org-governance")
INCOMPLETE = Findings(
    missing_documents=(
        MissingDocument("doc-c-assurance", "insurance_certificate", "Assurance.pdf"),
    ),
    completeness_findings=("Attestation d'assurance manquante.",),
    advisory_findings=("Aucun contact de sécurité distinct n'est indiqué.",),
)
HOSPITAL_C = HospitalApplication(
    "app-hospital-c",
    "org-hospital-c",
    ApplicationStatus.HUMAN_REVIEW,
    SUBMITTED,
    INCOMPLETE,
)
CLEAN = replace(HOSPITAL_C, findings=Findings())


def draft(**changes) -> DecisionDraft:
    values = {
        "outcome": Outcome.APPROVED,
        "rationale": "Dossier conforme, sous réserve de l'assurance.",
        "conditions": ("Transmettre l'attestation d'assurance.",),
        "findings_acknowledged": True,
    }
    return DecisionDraft(**{**values, **changes})


def issue_fields(application, d) -> list[str]:
    with pytest.raises(InvalidDecision) as raised:
        decide(application, OLFA, d, DEMO_POLICY, DEMO_NOW)
    return [i.field for i in raised.value.issues]


def test_approval_records_the_decision_and_decides_the_application():
    decision, decided = decide(HOSPITAL_C, OLFA, draft(), DEMO_POLICY, DEMO_NOW)

    assert decision.decision_ref == "dec-hospital-c"
    assert decision.organization_ref == "org-hospital-c"
    assert decision.outcome is Outcome.APPROVED
    assert decision.decided_by_ref == "usr-olfa"
    assert decision.decided_at == DEMO_NOW
    assert decision.conditions == ("Transmettre l'attestation d'assurance.",)
    assert decided.status is ApplicationStatus.APPROVED
    assert decided.decision_ref == "dec-hospital-c"


def test_rationale_and_conditions_are_trimmed_and_blank_conditions_dropped():
    decision, _ = decide(
        HOSPITAL_C,
        OLFA,
        draft(rationale="  " + "x" * 20 + "  ", conditions=("  A  ", "   ", "")),
        DEMO_POLICY,
        DEMO_NOW,
    )

    assert decision.rationale == "x" * 20
    assert decision.conditions == ("A",)


def test_rejection_needs_no_condition():
    decision, decided = decide(
        HOSPITAL_C,
        OLFA,
        draft(outcome=Outcome.REJECTED, conditions=()),
        DEMO_POLICY,
        DEMO_NOW,
    )

    assert decision.outcome is Outcome.REJECTED
    assert decided.status is ApplicationStatus.REJECTED


def test_every_broken_rule_is_reported_at_once():
    fields = issue_fields(
        HOSPITAL_C,
        draft(rationale="Trop court", conditions=(" ",), findings_acknowledged=False),
    )

    assert fields == ["rationale", "findings_acknowledged", "conditions"]


def test_rejection_with_a_condition_is_refused():
    assert issue_fields(HOSPITAL_C, draft(outcome=Outcome.REJECTED)) == ["conditions"]


def test_application_without_findings_needs_no_acknowledgement_or_condition():
    decision, _ = decide(
        CLEAN,
        OLFA,
        draft(conditions=(), findings_acknowledged=False),
        DEMO_POLICY,
        DEMO_NOW,
    )

    assert decision.conditions == ()


def test_advisory_findings_alone_need_acknowledgement_but_no_condition():
    advisory_only = replace(
        HOSPITAL_C, findings=Findings(advisory_findings=("Avis consultatif.",))
    )

    assert issue_fields(advisory_only, draft(findings_acknowledged=False)) == [
        "findings_acknowledged"
    ]
    decide(advisory_only, OLFA, draft(conditions=()), DEMO_POLICY, DEMO_NOW)


@pytest.mark.parametrize(
    "reviewer",
    [
        None,
        Reviewer("usr-mehdi", "hospital_manager", "org-hospital-c"),
        Reviewer("clin-x", "physician", "org-hospital-a"),
        # A governance reviewer who belongs to the applicant organization.
        Reviewer("usr-c-reviewer", "governance_reviewer", "org-hospital-c"),
    ],
)
def test_only_a_governance_reviewer_outside_the_applicant_may_decide(reviewer):
    with pytest.raises(ReviewerNotAllowed):
        decide(HOSPITAL_C, reviewer, draft(), DEMO_POLICY, DEMO_NOW)


@pytest.mark.parametrize(
    "status", [ApplicationStatus.PENDING, ApplicationStatus.APPROVED]
)
def test_only_an_application_in_human_review_can_be_decided(status):
    application = replace(
        HOSPITAL_C,
        status=status,
        decision_ref="dec-hospital-c" if status is ApplicationStatus.APPROVED else None,
    )

    with pytest.raises(NotAwaitingReview):
        decide(application, OLFA, draft(), DEMO_POLICY, DEMO_NOW)


def test_not_awaiting_review_is_checked_before_the_reviewer():
    approved = replace(
        HOSPITAL_C, status=ApplicationStatus.APPROVED, decision_ref="dec-hospital-c"
    )

    with pytest.raises(NotAwaitingReview):
        decide(approved, None, draft(), DEMO_POLICY, DEMO_NOW)


def test_findings_count_and_completeness():
    assert INCOMPLETE.count == 3
    assert INCOMPLETE.incomplete
    assert not Findings(unaccepted_agreements=()).incomplete
    assert Findings(unaccepted_agreements=("governance_charter",)).incomplete


@pytest.mark.parametrize(
    "changes",
    [
        {"application_ref": "hospital-c"},
        {"organization_ref": "org c"},
        {"submitted_at": datetime(2026, 10, 6, 15, 20)},
        # A decided application must cite its decision, and only then.
        {"status": ApplicationStatus.APPROVED},
        {"decision_ref": "dec-hospital-c"},
    ],
)
def test_application_invariants(changes):
    with pytest.raises(InvalidHospitalApplication):
        replace(HOSPITAL_C, **changes)
