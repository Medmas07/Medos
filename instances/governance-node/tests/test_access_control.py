"""HC-212's role matrix and its use case, with test doubles at the ports."""

import pytest

from adapters.outbound.in_memory_sessions import InMemorySessionStore
from application.access_control import authorize
from application.authentication import _key
from domain.access_control import (
    Permission,
    PermissionDenied,
    check_permission,
    permissions_of,
)
from domain.authentication import NotAuthenticated, Session
from domain.hospital_approval import Reviewer
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

    person = authorize(
        "token-usr-olfa", Permission.AUDIT, sessions, People(OLFA), lambda: DEMO_NOW
    )

    assert person == OLFA


def test_authorize_refuses_a_role_without_the_permission():
    sessions = signed_in("usr-aymen")

    with pytest.raises(PermissionDenied):
        authorize(
            "token-usr-aymen",
            Permission.REVIEW,
            sessions,
            People(AYMEN),
            lambda: DEMO_NOW,
        )


def test_authorize_needs_a_valid_session_first():
    with pytest.raises(NotAuthenticated):
        authorize(
            "token-usr-olfa",
            Permission.REVIEW,
            signed_in(),
            People(OLFA),
            lambda: DEMO_NOW,
        )


def test_authorize_refuses_a_session_whose_person_is_no_longer_known():
    with pytest.raises(NotAuthenticated):
        authorize(
            "token-usr-olfa",
            Permission.REVIEW,
            signed_in("usr-olfa"),
            People(),
            lambda: DEMO_NOW,
        )
