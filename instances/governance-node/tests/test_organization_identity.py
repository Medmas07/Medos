"""HC-213's organization identity rules and the fixture directory behind them."""

import json

import pytest

from adapters.outbound.fixture_organization_directory import (
    FixtureOrganizationDirectory,
)
from domain.hospital_approval import Reviewer
from domain.organization_identity import (
    AffiliationNotRecognized,
    Organization,
    OrganizationMismatch,
    OrganizationType,
    check_acts_for,
    check_affiliation,
)
from tests.conftest import DEMO_DATA

AUTHORITY = "org-governance"
GOVERNANCE = Organization("org-governance", OrganizationType.GOVERNANCE_AUTHORITY)
OTHER_AUTHORITY = Organization("org-gov-2", OrganizationType.GOVERNANCE_AUTHORITY)
HOSPITAL = Organization("org-hospital-a", OrganizationType.HOSPITAL)
PRACTICE = Organization("org-private-practice", OrganizationType.PRIVATE_PRACTICE)
LAB = Organization("org-research-lab", OrganizationType.RESEARCH_INSTITUTION)
PLATFORM = Organization("org-platform", OrganizationType.PLATFORM_OPERATOR)


def person(role: str, organization: Organization) -> Reviewer:
    return Reviewer("usr-test", role, organization.organization_ref)


# Affiliation


@pytest.mark.parametrize(
    ("role", "organization"),
    [
        ("governance_reviewer", GOVERNANCE),
        ("hospital_manager", HOSPITAL),
        ("hospital_manager", PRACTICE),
        ("physician", HOSPITAL),
        ("physician", PRACTICE),
        ("researcher", LAB),
        # Roles granting nothing here are only asked for a known organization.
        ("nurse", HOSPITAL),
    ],
)
def test_a_role_held_at_a_fitting_organization_is_recognized(role, organization):
    check_affiliation(person(role, organization), organization, AUTHORITY)


@pytest.mark.parametrize(
    ("role", "organization"),
    [
        # The company running the platform is not the Authority.
        ("governance_reviewer", PLATFORM),
        ("governance_reviewer", HOSPITAL),
        ("hospital_manager", LAB),
        ("hospital_manager", GOVERNANCE),
        ("physician", PLATFORM),
        ("researcher", HOSPITAL),
    ],
)
def test_a_role_held_at_an_organization_it_does_not_fit_is_refused(role, organization):
    with pytest.raises(AffiliationNotRecognized, match="is not held at a"):
        check_affiliation(person(role, organization), organization, AUTHORITY)


def test_a_reviewer_of_another_authority_does_not_review_here():
    reviewer = person("governance_reviewer", OTHER_AUTHORITY)

    with pytest.raises(AffiliationNotRecognized, match="not the Authority"):
        check_affiliation(reviewer, OTHER_AUTHORITY, AUTHORITY)


def test_an_unknown_organization_is_refused():
    with pytest.raises(AffiliationNotRecognized, match="unknown"):
        check_affiliation(person("physician", HOSPITAL), None, AUTHORITY)


# Acting for one's own organization


def test_a_person_acts_for_their_own_organization():
    check_acts_for(person("physician", HOSPITAL), "org-hospital-a", "field")


def test_a_person_does_not_act_for_another_organization():
    with pytest.raises(OrganizationMismatch) as error:
        check_acts_for(person("physician", HOSPITAL), "org-hospital-b", "requester_ref")

    assert str(error.value) == (
        "requester_ref org-hospital-b is not the signed-in person's organization "
        "org-hospital-a."
    )


# Fixture directory


def test_the_directory_knows_every_demo_organization_and_its_type():
    directory = FixtureOrganizationDirectory.load(DEMO_DATA / "organizations.json")

    assert directory.organization("org-hospital-c") == Organization(
        "org-hospital-c", OrganizationType.HOSPITAL
    )
    assert directory.organization("org-platform").type is (
        OrganizationType.PLATFORM_OPERATOR
    )
    assert directory.organization("org-unknown") is None


def test_every_demo_staff_member_and_clinician_is_recognized():
    directory = FixtureOrganizationDirectory.load(DEMO_DATA / "organizations.json")
    people = json.loads((DEMO_DATA / "people.json").read_text(encoding="utf-8"))

    for p in people["staff"] + people["clinicians"]:
        reviewer = Reviewer(p["id"], p["role"], p["organizationId"])
        check_affiliation(
            reviewer, directory.organization(p["organizationId"]), AUTHORITY
        )


def test_the_directory_refuses_a_file_not_marked_fictional(tmp_path):
    path = tmp_path / "organizations.json"
    path.write_text(json.dumps({"organizations": []}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="not marked fictional"):
        FixtureOrganizationDirectory.load(path)


def test_the_directory_refuses_an_unknown_organization_type(tmp_path):
    path = tmp_path / "organizations.json"
    path.write_text(
        json.dumps(
            {"fictional": True, "organizations": [{"id": "org-x", "type": "bank"}]}
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="invalid organization"):
        FixtureOrganizationDirectory.load(path)
