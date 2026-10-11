"""HC-212's role matrix and its use case, with test doubles at the ports."""

import pytest

from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from adapters.outbound.in_memory_sessions import InMemorySessionStore
from application.access_control import authorize
from application.authentication import _key
from domain.access_control import (
    Permission,
    PermissionDenied,
    check_permission,
    permissions_of,
)
from domain.audit import AuditAction, AuditDomain, AuditOutcome, SubjectType
from domain.authentication import NotAuthenticated, Session
from domain.hospital_approval import Reviewer
from domain.organization_identity import (
    AffiliationNotRecognized,
    Organization,
    OrganizationType,
)
from tests.conftest import DEMO_NOW

# Matrix


def test_a_governance_reviewer_reviews_and_reads_the_audit_trail():
    assert permissions_of("governance_reviewer") == {
        Permission.REVIEW,
        Permission.AUDIT,
    }


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        ("hospital_manager", Permission.REQUEST_SYNCHRONIZATION),
        ("physician", Permission.REQUEST_SYNCHRONIZATION),
        ("researcher", Permission.REQUEST_RESEARCH),
    ],
)
def test_requesters_only_submit(role, permission):
    assert permissions_of(role) == {permission}


@pytest.mark.parametrize("role", ["nurse", "patient", "relative", "unknown", ""])
def test_any_other_role_grants_nothing(role):
    assert permissions_of(role) == frozenset()


def test_no_role_both_requests_and_reviews():
    # Who asks is never who decides.
    for role in ("hospital_manager", "physician", "researcher", "governance_reviewer"):
        granted = permissions_of(role)
        asks = {Permission.REQUEST_SYNCHRONIZATION, Permission.REQUEST_RESEARCH}
        assert not (granted & asks and Permission.REVIEW in granted)


def test_check_permission_names_the_role_and_permission():
    with pytest.raises(PermissionDenied) as raised:
        check_permission("researcher", Permission.REVIEW)

    assert str(raised.value) == "The role researcher does not grant governance:review."


def test_the_review_rules_read_the_same_matrix():
    assert Reviewer("usr-olfa", "governance_reviewer", "org-governance").may_review
    assert not Reviewer("usr-mehdi", "hospital_manager", "org-hospital-a").may_review


# Use case

OLFA = Reviewer("usr-olfa", "governance_reviewer", "org-governance")
AYMEN = Reviewer("usr-aymen", "researcher", "org-research")
AUTHORITY = "org-governance"


class Organizations:
    def __init__(self, *organizations: Organization) -> None:
        self._organizations = {o.organization_ref: o for o in organizations}

    def organization(self, organization_ref: str) -> Organization | None:
        return self._organizations.get(organization_ref)


KNOWN = Organizations(
    Organization("org-governance", OrganizationType.GOVERNANCE_AUTHORITY),
    Organization("org-research", OrganizationType.RESEARCH_INSTITUTION),
)


class People:
    def __init__(self, *people: Reviewer) -> None:
        self._people = {p.person_ref: p for p in people}

    def reviewer(self, person_ref: str) -> Reviewer | None:
        return self._people.get(person_ref)


def signed_in(*person_refs: str) -> InMemorySessionStore:
    sessions = InMemorySessionStore()
    for ref in person_refs:
        sessions.add(_key(f"token-{ref}"), Session.start(ref, DEMO_NOW))
    return sessions


def test_authorize_returns_the_signed_in_person_when_their_role_grants_it():
    sessions = signed_in("usr-olfa")
    trail = InMemoryAuditTrail([])

    person = authorize(
        "token-usr-olfa",
        Permission.AUDIT,
        sessions,
        People(OLFA),
        KNOWN,
        AUTHORITY,
        lambda: DEMO_NOW,
        trail,
    )

    assert person == OLFA
    # Access granted is not an event.
    assert trail.events() == []


def test_authorize_refuses_a_role_without_the_permission():
    sessions = signed_in("usr-aymen")

    with pytest.raises(PermissionDenied):
        authorize(
            "token-usr-aymen",
            Permission.REVIEW,
            sessions,
            People(AYMEN),
            KNOWN,
            AUTHORITY,
            lambda: DEMO_NOW,
            InMemoryAuditTrail([]),
        )


def test_authorize_needs_a_valid_session_first():
    with pytest.raises(NotAuthenticated):
        authorize(
            "token-usr-olfa",
            Permission.REVIEW,
            signed_in(),
            People(OLFA),
            KNOWN,
            AUTHORITY,
            lambda: DEMO_NOW,
            InMemoryAuditTrail([]),
        )


def test_authorize_refuses_a_session_whose_person_is_no_longer_known():
    with pytest.raises(NotAuthenticated):
        authorize(
            "token-usr-olfa",
            Permission.REVIEW,
            signed_in("usr-olfa"),
            People(),
            KNOWN,
            AUTHORITY,
            lambda: DEMO_NOW,
            InMemoryAuditTrail([]),
        )


def test_authorize_refuses_a_person_whose_organization_is_not_recognized():
    sessions = signed_in("usr-olfa")

    with pytest.raises(AffiliationNotRecognized):
        authorize(
            "token-usr-olfa",
            Permission.REVIEW,
            sessions,
            People(OLFA),
            Organizations(),
            AUTHORITY,
            lambda: DEMO_NOW,
            InMemoryAuditTrail([]),
        )


def test_authorize_checks_the_role_before_the_organization():
    # A role without the permission is refused as such, whatever its organization.
    with pytest.raises(PermissionDenied):
        authorize(
            "token-usr-aymen",
            Permission.REVIEW,
            signed_in("usr-aymen"),
            People(AYMEN),
            Organizations(),
            AUTHORITY,
            lambda: DEMO_NOW,
            InMemoryAuditTrail([]),
        )


# HC-215: refusals of a signed-in person are audited; a missing session is not.


def denied_events(trail: InMemoryAuditTrail) -> list:
    return [(e.action, e.actor_ref, e.subject_ref, e.reason) for e in trail.events()]


@pytest.mark.parametrize(
    ("person", "organizations"),
    [(AYMEN, KNOWN), (OLFA, Organizations())],
    ids=["role", "organization"],
)
def test_a_refusal_is_recorded_without_the_request(person, organizations):
    trail = InMemoryAuditTrail([])

    with pytest.raises((PermissionDenied, AffiliationNotRecognized)):
        authorize(
            f"token-{person.person_ref}",
            Permission.REVIEW,
            signed_in(person.person_ref),
            People(person),
            organizations,
            AUTHORITY,
            lambda: DEMO_NOW,
            trail,
        )

    [event] = trail.events()
    assert (event.action, event.domain, event.subject_type, event.outcome) == (
        AuditAction.ACCESS_DENIED,
        AuditDomain.SECURITY,
        SubjectType.PERMISSION,
        AuditOutcome.DENIED,
    )
    assert (event.actor_ref, event.subject_ref, event.reason) == (
        person.person_ref,
        "governance:review",
        "permission_denied",
    )
    assert event.recorded_at == DEMO_NOW
    assert event.organization_refs == tuple(
        dict.fromkeys((AUTHORITY, person.organization_ref))
    )


def test_no_session_is_not_recorded():
    # Nobody is known: recording it would let anyone grow the trail.
    trail = InMemoryAuditTrail([])

    with pytest.raises(NotAuthenticated):
        authorize(
            "token-usr-olfa",
            Permission.REVIEW,
            signed_in(),
            People(OLFA),
            KNOWN,
            AUTHORITY,
            lambda: DEMO_NOW,
            trail,
        )

    assert denied_events(trail) == []
