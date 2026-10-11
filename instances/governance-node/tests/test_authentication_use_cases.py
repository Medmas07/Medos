"""HC-211 use cases with test doubles at their ports: no hashing, no HTTP."""

import hashlib
from datetime import timedelta

import pytest

from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from adapters.outbound.in_memory_sessions import InMemorySessionStore
from application.authentication import authenticate, sign_in, sign_out
from domain.authentication import (
    LOCKOUT,
    MAX_FAILURES,
    AuthenticationFailed,
    NotAuthenticated,
    SignInThrottle,
)
from domain.hospital_approval import Reviewer
from tests.conftest import DEMO_NOW

OLFA = Reviewer("usr-olfa", "governance_reviewer", "org-governance")


class Credentials:
    def __init__(self, **hashes: str) -> None:
        self._hashes = {k.replace("_", "-"): v for k, v in hashes.items()}

    def password_hash(self, person_ref: str) -> str | None:
        return self._hashes.get(person_ref)


class Hasher:
    """Stored hash 'plain:<password>'; records what it was asked to verify."""

    def __init__(self) -> None:
        self.calls: list[str | None] = []

    def verify(self, password: str, encoded: str | None) -> bool:
        self.calls.append(encoded)
        return encoded == f"plain:{password}"


class People:
    def reviewer(self, person_ref: str) -> Reviewer | None:
        return OLFA if person_ref == "usr-olfa" else None


@pytest.fixture
def world():
    return {
        "credentials": Credentials(usr_olfa="plain:right"),
        "hasher": Hasher(),
        "people": People(),
        "sessions": InMemorySessionStore(),
        "throttle": SignInThrottle(),
        "clock": lambda: DEMO_NOW,
        "trail": InMemoryAuditTrail([]),
        "authority_ref": "org-governance",
    }


def attempt(world, person_ref="usr-olfa", password="right", **changes):
    kwargs = {**world, "new_token": lambda: "t" * 43, **changes}
    return sign_in(person_ref, password, **kwargs)


def test_sign_in_starts_a_session_kept_only_by_its_token_digest(world):
    signed_in = attempt(world)

    assert signed_in.token == "t" * 43
    assert signed_in.person == OLFA
    assert signed_in.session.issued_at == DEMO_NOW
    digest = hashlib.sha256(signed_in.token.encode()).hexdigest()
    assert world["sessions"].get(digest) == signed_in.session
    assert world["sessions"].get(signed_in.token) is None


def test_a_wrong_password_fails_and_counts(world):
    with pytest.raises(AuthenticationFailed):
        attempt(world, password="wrong")

    assert world["throttle"]._accounts["usr-olfa"].failures == 1


def test_an_unknown_person_fails_after_a_verification_all_the_same(world):
    with pytest.raises(AuthenticationFailed):
        attempt(world, person_ref="usr-nobody")

    assert world["hasher"].calls == [None]
    # Unknown references are not tracked, so they cannot fill the throttle.
    assert world["throttle"]._accounts == {}


def test_a_locked_account_fails_even_with_the_right_password(world):
    for _ in range(MAX_FAILURES):
        with pytest.raises(AuthenticationFailed):
            attempt(world, password="wrong")

    with pytest.raises(AuthenticationFailed):
        attempt(world)

    # The stored hash is not verified while locked, but a verification still runs.
    assert world["hasher"].calls[-1] is None


def test_authenticate_returns_the_session_until_it_expires(world):
    signed_in = attempt(world)

    assert authenticate(signed_in.token, world["sessions"], world["clock"]) == (
        signed_in.session
    )
    after = signed_in.session.expires_at
    with pytest.raises(NotAuthenticated, match="expired"):
        authenticate(signed_in.token, world["sessions"], lambda: after)
    # An expired session is gone.
    with pytest.raises(NotAuthenticated, match="unknown"):
        authenticate(signed_in.token, world["sessions"], world["clock"])


def test_an_unknown_token_does_not_authenticate(world):
    with pytest.raises(NotAuthenticated):
        authenticate("not-a-session", world["sessions"], world["clock"])


def test_sign_out_ends_the_session(world):
    signed_in = attempt(world)

    sign_out(signed_in.token, world["sessions"], world["clock"])

    with pytest.raises(NotAuthenticated):
        authenticate(signed_in.token, world["sessions"], world["clock"])
    with pytest.raises(NotAuthenticated):
        sign_out(signed_in.token, world["sessions"], world["clock"])


def test_the_store_drops_sessions_expired_when_a_new_one_starts(world):
    first = attempt(world)
    later = DEMO_NOW + timedelta(hours=9)

    attempt(world, clock=lambda: later, new_token=lambda: "u" * 43)

    assert len(world["sessions"]._sessions) == 1
    with pytest.raises(NotAuthenticated, match="unknown"):
        authenticate(first.token, world["sessions"], lambda: later)


# HC-215: sign-ins are audited, within bounds.


def recorded(world) -> list[tuple]:
    return [
        (e.action.value, e.subject_ref, e.reason, e.organization_refs)
        for e in world["trail"].events()
    ]


def test_a_sign_in_is_recorded_without_its_password_or_token(world):
    signed_in = attempt(world)

    [event] = world["trail"].events()
    assert recorded(world) == [("signed_in", "usr-olfa", None, ("org-governance",))]
    assert event.actor_ref == "usr-olfa"
    assert event.recorded_at == DEMO_NOW
    assert signed_in.token not in repr(event) and "right" not in repr(event)


def test_failures_are_recorded_until_the_one_that_locks(world):
    for _ in range(MAX_FAILURES):
        with pytest.raises(AuthenticationFailed):
            attempt(world, password="wrong")

    reasons = [reason for _, _, reason, _ in recorded(world)]
    assert reasons == ["invalid_credentials"] * (MAX_FAILURES - 1) + ["account_locked"]


def test_attempts_on_a_locked_account_are_not_recorded(world):
    for _ in range(MAX_FAILURES):
        with pytest.raises(AuthenticationFailed):
            attempt(world, password="wrong")

    for password in ("wrong", "right"):
        with pytest.raises(AuthenticationFailed):
            attempt(world, password=password)

    assert len(world["trail"].events()) == MAX_FAILURES


def test_an_unknown_person_is_not_recorded(world):
    # Any reference can be tried: recording them would let anyone grow the trail.
    with pytest.raises(AuthenticationFailed):
        attempt(world, person_ref="usr-nobody")

    assert world["trail"].events() == []


def test_failures_are_recorded_again_once_the_lock_ends(world):
    for _ in range(MAX_FAILURES):
        with pytest.raises(AuthenticationFailed):
            attempt(world, password="wrong")
    later = DEMO_NOW + LOCKOUT

    with pytest.raises(AuthenticationFailed):
        attempt(world, password="wrong", clock=lambda: later)

    assert recorded(world)[-1][2] == "invalid_credentials"
