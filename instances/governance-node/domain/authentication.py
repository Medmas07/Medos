"""Who is calling the Governance Node: sessions and sign-in throttling (HC-211, ADR-0008).

A person signs in with a password and gets a bearer session that expires. Repeated
failures lock the account for a while, whatever password is tried next. Passwords,
tokens, and their hashing stay outside the domain.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

# How long a session lasts after sign-in; there is no renewal, the person signs in again.
SESSION_LIFETIME = timedelta(hours=8)
# Failed sign-ins in a row that lock an account, and for how long.
MAX_FAILURES = 5
LOCKOUT = timedelta(minutes=15)


class AuthenticationFailed(Exception):
    """Unknown person, wrong password, or locked account: one answer for all three."""


class NotAuthenticated(Exception):
    """No session, an unknown one, or an expired one."""


@dataclass(frozen=True)
class Session:
    person_ref: str
    issued_at: datetime
    expires_at: datetime

    @classmethod
    def start(cls, person_ref: str, now: datetime) -> "Session":
        return cls(person_ref, now, now + SESSION_LIFETIME)

    def expired(self, now: datetime) -> bool:
        return now >= self.expires_at


@dataclass
class _Attempts:
    failures: int = 0
    locked_until: datetime | None = None


@dataclass
class SignInThrottle:
    """Failed sign-ins per account, held in memory: a restart unlocks every account."""

    _accounts: dict[str, _Attempts] = field(default_factory=dict)

    def locked(self, person_ref: str, now: datetime) -> bool:
        attempts = self._accounts.get(person_ref)
        return bool(attempts and attempts.locked_until and now < attempts.locked_until)

    def failed(self, person_ref: str, now: datetime) -> None:
        attempts = self._accounts.setdefault(person_ref, _Attempts())
        if attempts.locked_until and now >= attempts.locked_until:
            attempts.failures, attempts.locked_until = 0, None
        attempts.failures += 1
        if attempts.failures >= MAX_FAILURES:
            attempts.locked_until = now + LOCKOUT

    def succeeded(self, person_ref: str) -> None:
        self._accounts.pop(person_ref, None)
