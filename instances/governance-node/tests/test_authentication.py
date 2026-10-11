from datetime import timedelta

from domain.authentication import (
    LOCKOUT,
    MAX_FAILURES,
    SESSION_LIFETIME,
    Session,
    SignInThrottle,
)
from tests.conftest import DEMO_NOW


def test_a_session_lasts_eight_hours_from_sign_in():
    session = Session.start("usr-olfa", DEMO_NOW)

    assert (
        session.expires_at - session.issued_at == SESSION_LIFETIME == timedelta(hours=8)
    )
    assert not session.expired(session.expires_at - timedelta(seconds=1))
    assert session.expired(session.expires_at)


def test_an_account_locks_after_five_failures_in_a_row():
    throttle = SignInThrottle()
    for _ in range(MAX_FAILURES - 1):
        throttle.failed("usr-olfa", DEMO_NOW)
    assert not throttle.locked("usr-olfa", DEMO_NOW)

    throttle.failed("usr-olfa", DEMO_NOW)

    assert throttle.locked("usr-olfa", DEMO_NOW)
    assert not throttle.locked("usr-mehdi", DEMO_NOW)


def test_a_lock_ends_after_fifteen_minutes_and_counting_starts_again():
    throttle = SignInThrottle()
    for _ in range(MAX_FAILURES):
        throttle.failed("usr-olfa", DEMO_NOW)
    later = DEMO_NOW + LOCKOUT

    assert throttle.locked("usr-olfa", later - timedelta(seconds=1))
    assert not throttle.locked("usr-olfa", later)
    throttle.failed("usr-olfa", later)
    assert not throttle.locked("usr-olfa", later)


def test_a_successful_sign_in_resets_the_failures():
    throttle = SignInThrottle()
    for _ in range(MAX_FAILURES - 1):
        throttle.failed("usr-olfa", DEMO_NOW)

    throttle.succeeded("usr-olfa")
    throttle.failed("usr-olfa", DEMO_NOW)

    assert not throttle.locked("usr-olfa", DEMO_NOW)
