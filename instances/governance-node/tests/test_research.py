from dataclasses import replace
from datetime import date, datetime

import pytest

from domain.hospital_approval import (
    InvalidDecision,
    Outcome,
    Reviewer,
    ReviewerNotAllowed,
)
from domain.research import (
    CheckState,
    DataScope,
    DenialReason,
    InvalidResearchRequest,
    JobAsk,
    NotUnderReview,
    Population,
    RequestStatus,
    ResearchDecisionDraft,
    ResearchRequest,
    add_months,
    check_authorization,
    checks,
    decide,
    eligible_organizations,
    status_at,
)
from tests.test_policy import DEMO_POLICY
from tests.conftest import DEMO_NOW

APPROVED_ORGS = frozenset({"org-hospital-a", "org-hospital-b", "org-private-practice"})
PROJECT_1_POPULATION = Population(40, 79, date(2024, 1, 1), date(2026, 12, 31))
RAR = ResearchRequest(
    request_ref="rar-001",
    project_ref="proj-001",
    project_title="Facteurs de risque cardiométaboliques",
    research_organization_ref="org-research-lab",
    principal_investigator_ref="usr-aymen",
    submitted_by_ref="usr-aymen",
    purpose="Décrire le contrôle glycémique selon l'âge.",
    participating_organization_refs=(
        "org-hospital-a",
        "org-hospital-b",
        "org-hospital-c",
    ),
    data_scope=DataScope(
        PROJECT_1_POPULATION, ("age_band", "sex", "hba1c", "treated_hypertension")
    ),
    protocol_document_ref="doc-proj-001-protocole",
    submitted_at=datetime.fromisoformat("2026-07-01T10:00:00+01:00"),
)
OLFA = Reviewer("usr-olfa", "governance_reviewer", "org-governance")
APPROVE = ResearchDecisionDraft(
    Outcome.APPROVED,
    "Protocole conforme, périmètre proportionné.",
    (),
    ("org-hospital-b", "org-hospital-a"),
    ("hba1c", "age_band"),
    12,
    10,
)
REJECT = ResearchDecisionDraft(
    Outcome.REJECTED, "Finalité non démontrée à ce stade.", (), None, None, None, None
)


def issue_fields(draft, request=RAR, orgs=APPROVED_ORGS) -> list[str]:
    with pytest.raises(InvalidDecision) as raised:
        decide(request, None, OLFA, draft, orgs, DEMO_POLICY, DEMO_NOW)
    return [i.field for i in raised.value.issues]


def test_only_approved_participants_are_eligible():
    assert eligible_organizations(RAR, APPROVED_ORGS) == (
        "org-hospital-a",
        "org-hospital-b",
    )
    states = {c.check: c for c in checks(RAR, APPROVED_ORGS)}
    assert states["protocol"].state is CheckState.PASS
    assert states["organizations"].detail == (
        "org-hospital-a, org-hospital-b approved by the Authority; "
        "org-hospital-c excluded, not approved."
    )


def test_checks_fail_without_protocol_or_approved_participant():
    states = {
        c.check: c.state
        for c in checks(replace(RAR, protocol_document_ref=None), frozenset())
    }

    assert states == {"protocol": CheckState.FAIL, "organizations": CheckState.FAIL}


def test_approval_narrows_in_the_request_order():
    decision, decided = decide(
        RAR, None, OLFA, APPROVE, APPROVED_ORGS, DEMO_POLICY, DEMO_NOW
    )

    assert decision.decision_ref == decided.decision_ref == "dec-rar-001"
    assert decision.approved_organization_refs == ("org-hospital-a", "org-hospital-b")
    assert decision.approved_variables == ("age_band", "hba1c")
    assert decision.minimum_cell_size == 10
    assert decision.valid_until == datetime.fromisoformat("2027-10-10T10:00:00+01:00")
    assert status_at(decision, DEMO_NOW) is RequestStatus.AUTHORIZED
    assert status_at(decision, decision.valid_until) is RequestStatus.EXPIRED


@pytest.mark.parametrize(
    "start, months, end",
    [
        ("2026-01-31T10:00:00+01:00", 1, "2026-02-28T10:00:00+01:00"),
        ("2026-10-10T10:00:00+01:00", 6, "2027-04-10T10:00:00+01:00"),
        ("2026-12-15T10:00:00+01:00", 12, "2027-12-15T10:00:00+01:00"),
    ],
)
def test_validity_is_counted_in_calendar_months(start, months, end):
    assert add_months(datetime.fromisoformat(start), months) == datetime.fromisoformat(
        end
    )


def test_rejection_authorizes_nothing():
    decision, _ = decide(RAR, None, OLFA, REJECT, frozenset(), DEMO_POLICY, DEMO_NOW)

    assert (decision.approved_variables, decision.valid_until) == ((), None)
    assert status_at(decision, DEMO_NOW) is RequestStatus.REJECTED
    assert issue_fields(replace(REJECT, conditions=("x",), minimum_cell_size=10)) == [
        "conditions",
        "minimum_cell_size",
    ]


def test_an_approval_cannot_widen_the_request():
    widened = replace(
        APPROVE,
        approved_organization_refs=("org-hospital-c",),
        approved_variables=("diagnosis",),
        validity_months=13,
        minimum_cell_size=5,
    )

    assert issue_fields(widened) == [
        "approved_organization_refs",
        "approved_variables",
        "validity_months",
        "minimum_cell_size",
    ]
    assert issue_fields(replace(APPROVE, approved_variables=())) == [
        "approved_variables"
    ]
    assert issue_fields(replace(APPROVE, validity_months=None, rationale="court")) == [
        "rationale",
        "validity_months",
    ]


def test_approval_while_a_check_fails_is_refused():
    assert issue_fields(replace(APPROVE), orgs=frozenset()) == [
        "checks",
        "approved_organization_refs",
    ]


@pytest.mark.parametrize(
    "reviewer",
    [
        None,
        Reviewer("usr-aymen", "researcher", "org-research-lab"),
        Reviewer("usr-lab", "governance_reviewer", "org-research-lab"),
        Reviewer("usr-b", "governance_reviewer", "org-hospital-b"),
        # Even a hospital not yet approved is a participant.
        Reviewer("usr-c", "governance_reviewer", "org-hospital-c"),
    ],
)
def test_only_an_uninvolved_governance_reviewer_decides(reviewer):
    with pytest.raises(ReviewerNotAllowed):
        decide(RAR, None, reviewer, APPROVE, APPROVED_ORGS, DEMO_POLICY, DEMO_NOW)


def test_a_reviewer_who_submitted_may_not_decide():
    submitted_by_reviewer = replace(RAR, submitted_by_ref="usr-olfa")

    with pytest.raises(ReviewerNotAllowed):
        decide(
            submitted_by_reviewer,
            None,
            OLFA,
            APPROVE,
            APPROVED_ORGS,
            DEMO_POLICY,
            DEMO_NOW,
        )


def test_a_decided_request_is_not_under_review():
    decision, decided = decide(
        RAR, None, OLFA, APPROVE, APPROVED_ORGS, DEMO_POLICY, DEMO_NOW
    )

    with pytest.raises(NotUnderReview, match="rar-001 is approved"):
        decide(decided, decision, OLFA, REJECT, APPROVED_ORGS, DEMO_POLICY, DEMO_NOW)


@pytest.mark.parametrize(
    "changes",
    [
        {"request_ref": "001"},
        {"project_title": " "},
        {"participating_organization_refs": ()},
        {"participating_organization_refs": ("org-hospital-a", "org-hospital-a")},
        {"principal_investigator_ref": "Dr Aymen Rezgui"},
        {"submitted_at": datetime(2026, 7, 1, 10)},
    ],
)
def test_request_invariants(changes):
    with pytest.raises(InvalidResearchRequest):
        replace(RAR, **changes)


@pytest.mark.parametrize(
    "build",
    [
        lambda: Population(),
        lambda: Population(age_min=50, age_max=40),
        lambda: Population(
            encounter_from=date(2026, 1, 2), encounter_to=date(2026, 1, 1)
        ),
        lambda: Population(age_max=131),
        lambda: DataScope(Population(age_min=1), ()),
        lambda: DataScope(Population(age_min=1), ("hba1c", "hba1c")),
        lambda: DataScope(Population(age_min=1), ("HbA1c %",)),
    ],
)
def test_scope_invariants(build):
    with pytest.raises(InvalidResearchRequest):
        build()


JOB_001 = JobAsk(
    "proj-001",
    "usr-aymen",
    "Aggregate cardiometabolic risk research",
    frozenset({"org-hospital-a", "org-hospital-b"}),
    PROJECT_1_POPULATION,
    frozenset({"age_band", "hba1c"}),
)


def approved():
    return decide(RAR, None, OLFA, APPROVE, APPROVED_ORGS, DEMO_POLICY, DEMO_NOW)


def test_the_approval_authorizes_job_001():
    decision, request = approved()

    assert check_authorization(decision, request, JOB_001, DEMO_NOW).approved


@pytest.mark.parametrize(
    "changes, at, reason",
    [
        (
            {},
            datetime.fromisoformat("2026-10-10T09:59:59+01:00"),
            DenialReason.NOT_YET_VALID,
        ),
        ({}, datetime.fromisoformat("2027-10-10T10:00:00+01:00"), DenialReason.EXPIRED),
        ({"project_ref": "proj-002"}, DEMO_NOW, DenialReason.PROJECT_MISMATCH),
        ({"requested_by": "usr-olfa"}, DEMO_NOW, DenialReason.REQUESTER_MISMATCH),
        (
            {"target_organization_refs": frozenset({"org-hospital-c"})},
            DEMO_NOW,
            DenialReason.ORGANIZATION_NOT_APPROVED,
        ),
        (
            {"variables": frozenset({"sex"})},
            DEMO_NOW,
            DenialReason.VARIABLE_NOT_APPROVED,
        ),
        (
            {"population": Population(30, 79, date(2024, 1, 1), date(2026, 12, 31))},
            DEMO_NOW,
            DenialReason.POPULATION_EXCEEDED,
        ),
        (
            # A bound left open where the request set one is wider.
            {"population": Population(age_min=40, age_max=79)},
            DEMO_NOW,
            DenialReason.POPULATION_EXCEEDED,
        ),
        # The first failing reason wins.
        (
            {"project_ref": "proj-002", "variables": frozenset({"sex"})},
            DEMO_NOW,
            DenialReason.PROJECT_MISMATCH,
        ),
    ],
)
def test_each_difference_denies(changes, at, reason):
    decision, request = approved()

    assert (
        check_authorization(decision, request, replace(JOB_001, **changes), at).reason
        is reason
    )


def test_a_narrower_population_is_covered():
    decision, request = approved()
    narrower = replace(
        JOB_001, population=Population(50, 59, date(2025, 1, 1), date(2025, 12, 31))
    )

    assert check_authorization(decision, request, narrower, DEMO_NOW).approved


def test_a_rejection_denies():
    decision, request = decide(
        RAR, None, OLFA, REJECT, APPROVED_ORGS, DEMO_POLICY, DEMO_NOW
    )

    assert check_authorization(decision, request, JOB_001, DEMO_NOW).reason is (
        DenialReason.NOT_APPROVED
    )
