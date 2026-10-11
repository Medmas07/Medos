"""HC-211 use cases: sign in, authenticate a bearer token, sign out (ADR-0010).

The Governance Node authenticates the people who act on it, from its own credentials.
A session token is random, given to the caller once, and kept here only as its
SHA-256 digest, so a store's contents cannot be replayed as tokens.

Sign-ins are audited (HC-215): each success, and each refusal that counts against a
known account, the one that locks it named `account_locked`. Refusals for an unknown
person or a locked account are not recorded, so no caller can grow the trail without
bound; the throttle already limits the others to five per account per lockout.
"""

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from application.audit import AuditTrail, record
from application.hospital_approval import ReviewerDirectory
from domain.audit import AuditAction, AuditDomain, AuditOutcome, SubjectType
from domain.authentication import (
    AuthenticationFailed,
    NotAuthenticated,
    Session,
    SignInThrottle,
)
from domain.hospital_approval import Reviewer


class CredentialStore(Protocol):
    def password_hash(self, person_ref: str) -> str | None: ...


class PasswordHasher(Protocol):
    def verify(self, password: str, encoded: str | None) -> bool:
        """False for a wrong password. With no stored hash, it still spends the time
        of a verification and answers False, so timing does not reveal accounts."""
        ...


class SessionStore(Protocol):
    def add(self, key: str, session: Session) -> None: ...
    def get(self, key: str) -> Session | None: ...
    def remove(self, key: str) -> None: ...


@dataclass(frozen=True)
class SignedIn:
    token: str
    session: Session
    person: Reviewer


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def sign_in(
    person_ref: str,
    password: str,
    credentials: CredentialStore,
    hasher: PasswordHasher,
    people: ReviewerDirectory,
    sessions: SessionStore,
    throttle: SignInThrottle,
    clock: Callable[[], datetime],
    trail: AuditTrail,
    authority_ref: str,
    new_token: Callable[[], str] = _new_token,
) -> SignedIn:
    now = clock()
    encoded = credentials.password_hash(person_ref)
    locked = encoded is not None and throttle.locked(person_ref, now)
    # Verify even when the answer is already known, so every failure takes as long.
    verified = hasher.verify(password, None if locked else encoded)
    person = people.reviewer(person_ref)
    organizations = (authority_ref,) + ((person.organization_ref,) if person else ())

    def audit(action: AuditAction, reason: str | None = None) -> None:
        record(
            trail,
            now,
            action,
            AuditDomain.SECURITY,
            person_ref,
            SubjectType.PERSON,
            person_ref,
            organizations,
            AuditOutcome.DENIED if reason else None,
            reason,
        )

    if locked or not verified or person is None:
        if encoded is not None and not locked:
            locks = throttle.failed(person_ref, now)
            audit(
                AuditAction.SIGN_IN_REFUSED,
                "account_locked" if locks else "invalid_credentials",
            )
        raise AuthenticationFailed()
    throttle.succeeded(person_ref)
    token = new_token()
    session = Session.start(person_ref, now)
    # No audit, no session.
    audit(AuditAction.SIGNED_IN)
    sessions.add(_key(token), session)
    return SignedIn(token, session, person)


def authenticate(
    token: str, sessions: SessionStore, clock: Callable[[], datetime]
) -> Session:
    key = _key(token)
    session = sessions.get(key)
    if session is None:
        raise NotAuthenticated("The session is unknown or has ended.")
    if session.expired(clock()):
        sessions.remove(key)
        raise NotAuthenticated("The session has expired.")
    return session


def sign_out(token: str, sessions: SessionStore, clock: Callable[[], datetime]) -> None:
    authenticate(token, sessions, clock)
    sessions.remove(_key(token))
