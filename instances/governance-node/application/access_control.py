"""HC-212 use case: may the signed-in person do this at the Governance Node?

The session says who is calling (HC-211); the people directory gives their role and
organization; the domain's role matrix says what the role grants; the organization
directory says whether the role is held at a recognized organization (HC-213). Deny by
default.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from application.authentication import SessionStore, authenticate
from application.hospital_approval import ReviewerDirectory
from domain.access_control import Permission, check_permission
from domain.authentication import NotAuthenticated
from domain.hospital_approval import Reviewer
from domain.organization_identity import Organization, check_affiliation


class OrganizationDirectory(Protocol):
    def organization(self, organization_ref: str) -> Organization | None: ...


def authorize(
    token: str,
    permission: Permission,
    sessions: SessionStore,
    people: ReviewerDirectory,
    organizations: OrganizationDirectory,
    authority_ref: str,
    clock: Callable[[], datetime],
) -> Reviewer:
    """The signed-in person, if their role grants `permission` and is held at a
    recognized organization. Raises NotAuthenticated without a valid session,
    PermissionDenied or AffiliationNotRecognized otherwise."""
    session = authenticate(token, sessions, clock)
    person = people.reviewer(session.person_ref)
    if person is None:
        raise NotAuthenticated("The signed-in person is unknown.")
    check_permission(person.role, permission)
    check_affiliation(
        person, organizations.organization(person.organization_ref), authority_ref
    )
    return person
