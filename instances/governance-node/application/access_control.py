"""HC-212 use case: may the signed-in person do this at the Governance Node?

The session says who is calling (HC-211); the people directory gives their role and
organization; the domain's role matrix says what the role grants; the organization
directory says whether the role is held at a recognized organization (HC-213). Deny by
default. Each refusal of a signed-in person is recorded in the audit trail (HC-215).
"""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from application.audit import AuditTrail, record
from application.authentication import SessionStore, authenticate
from application.hospital_approval import ReviewerDirectory
from domain.access_control import Permission, PermissionDenied, check_permission
from domain.audit import AuditAction, AuditDomain, AuditOutcome, SubjectType
from domain.authentication import NotAuthenticated
from domain.hospital_approval import Reviewer
from domain.organization_identity import (
    AffiliationNotRecognized,
    Organization,
    check_affiliation,
)


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
    trail: AuditTrail,
) -> Reviewer:
    """The signed-in person, if their role grants `permission` and is held at a
    recognized organization. Raises NotAuthenticated without a valid session (not
    audited: nobody is known), PermissionDenied or AffiliationNotRecognized otherwise
    (audited)."""
    session = authenticate(token, sessions, clock)
    person = people.reviewer(session.person_ref)
    if person is None:
        raise NotAuthenticated("The signed-in person is unknown.")
    try:
        check_permission(person.role, permission)
        check_affiliation(
            person, organizations.organization(person.organization_ref), authority_ref
        )
    except (PermissionDenied, AffiliationNotRecognized):
        record_denial(
            trail, clock(), person, permission, "permission_denied", authority_ref
        )
        raise
    return person


def record_denial(
    trail: AuditTrail,
    at: datetime,
    person: Reviewer,
    permission: Permission,
    reason: str,
    authority_ref: str,
) -> None:
    """Record that a signed-in person was refused what `permission` protects: by role
    or organization (`permission_denied`), or for declaring another person or
    organization than their own (`reviewer_mismatch`, `submitter_mismatch`,
    `organization_mismatch`). Never the request's content."""
    record(
        trail,
        at,
        AuditAction.ACCESS_DENIED,
        AuditDomain.SECURITY,
        person.person_ref,
        SubjectType.PERMISSION,
        permission.value,
        (authority_ref, person.organization_ref),
        AuditOutcome.DENIED,
        reason,
    )
