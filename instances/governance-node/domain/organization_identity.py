"""Which organization a person acts for at the Governance Node (HC-213, ADR-0012).

The Authority keeps the identity of the institutions it governs: each has a type. A
person's role is held at their organization, and only fits some types of organization:
a governance reviewer belongs to this Node's own Authority, a hospital manager or a
physician to a hospital or a private practice, a researcher to a research institution.
An affiliation that does not fit grants nothing. A person acts only for their own
organization: what they submit names it, never another one.
"""

from dataclasses import dataclass
from enum import Enum

from domain.hospital_approval import Reviewer


class OrganizationType(str, Enum):
    HOSPITAL = "hospital"
    PRIVATE_PRACTICE = "private_practice"
    GOVERNANCE_AUTHORITY = "governance_authority"
    # The company running the platform: never the Authority, never a care provider.
    PLATFORM_OPERATOR = "platform_operator"
    RESEARCH_INSTITUTION = "research_institution"


@dataclass(frozen=True)
class Organization:
    organization_ref: str
    type: OrganizationType


_CARE_PROVIDERS = frozenset(
    {OrganizationType.HOSPITAL, OrganizationType.PRIVATE_PRACTICE}
)

# The organizations each role of the matrix (domain/access_control.py) is held at.
ROLE_ORGANIZATION_TYPES: dict[str, frozenset[OrganizationType]] = {
    "governance_reviewer": frozenset({OrganizationType.GOVERNANCE_AUTHORITY}),
    "hospital_manager": _CARE_PROVIDERS,
    "physician": _CARE_PROVIDERS,
    "researcher": frozenset({OrganizationType.RESEARCH_INSTITUTION}),
}


class AffiliationNotRecognized(Exception):
    pass


class OrganizationMismatch(Exception):
    def __init__(self, field: str, declared_ref: str, organization_ref: str) -> None:
        super().__init__(
            f"{field} {declared_ref} is not the signed-in person's organization "
            f"{organization_ref}."
        )


def check_affiliation(
    person: Reviewer, organization: Organization | None, authority_ref: str
) -> None:
    """The person's organization is known and fits their role. A governance reviewer
    reviews only for the Authority this Node runs for (`authority_ref`)."""
    if organization is None:
        raise AffiliationNotRecognized(
            f"The organization {person.organization_ref} of {person.person_ref} is "
            "unknown to the Governance Node."
        )
    allowed = ROLE_ORGANIZATION_TYPES.get(person.role)
    if allowed is not None and organization.type not in allowed:
        raise AffiliationNotRecognized(
            f"The role {person.role} is not held at a {organization.type.value} "
            f"organization ({organization.organization_ref})."
        )
    if (
        organization.type is OrganizationType.GOVERNANCE_AUTHORITY
        and organization.organization_ref != authority_ref
    ):
        raise AffiliationNotRecognized(
            f"{organization.organization_ref} is not the Authority this Governance "
            f"Node runs for ({authority_ref})."
        )


def check_acts_for(person: Reviewer, declared_ref: str, field: str) -> None:
    """What the person submits names their own organization."""
    if declared_ref != person.organization_ref:
        raise OrganizationMismatch(field, declared_ref, person.organization_ref)
