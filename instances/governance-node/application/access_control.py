"""HC-212 use case: may the signed-in person do this at the Governance Node?

The session says who is calling (HC-211); the people directory gives their role; the
domain's role matrix says what the role grants. Deny by default.
"""

from collections.abc import Callable
from datetime import datetime

from application.authentication import SessionStore, authenticate
from application.hospital_approval import ReviewerDirectory
from domain.access_control import Permission, check_permission
from domain.authentication import NotAuthenticated
from domain.hospital_approval import Reviewer


def authorize(
    token: str,
    permission: Permission,
    sessions: SessionStore,
    people: ReviewerDirectory,
    clock: Callable[[], datetime],
) -> Reviewer:
    """The signed-in person, if their role grants `permission`. Raises
    NotAuthenticated without a valid session, PermissionDenied otherwise."""
    session = authenticate(token, sessions, clock)
    person = people.reviewer(session.person_ref)
    if person is None:
        raise NotAuthenticated("The signed-in person is unknown.")
    check_permission(person.role, permission)
    return person
