"""A patient's access grants on this node: list, grant, revoke (HC-115).

Follows contracts/api/patient-access/patient-access-grants.v1.yaml. A grant recorded
here is enforced by this node's patient history queries, and by no other node. Who may
call these use cases is OPEN: requests are not authenticated. Grant changes are not
audit events of hospital-audit-events.v1 (HC-116), which covers queries only.
"""

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from domain.access_grant import AccessGrant, InvalidAccessGrant
from domain.patient_history import ScopeItem


class AccessGrantStore(Protocol):
    """The grants this node records and enforces."""

    mocked: bool

    def get(self, grant_ref: str) -> AccessGrant | None: ...

    def of_patient(self, patient_ref: str) -> tuple[AccessGrant, ...]: ...

    def save(self, grant: AccessGrant) -> None:
        """Adds the grant, or replaces the one with the same grant_ref."""
        ...


class GrantNotFound(Exception):
    """Unknown here, or another patient's: both look the same."""


def _new_grant_ref() -> str:
    return f"grant-{uuid.uuid4().hex}"


def list_access_grants(
    patient_ref: str, store: AccessGrantStore
) -> tuple[AccessGrant, ...]:
    """Newest first, including expired and revoked grants."""
    return tuple(
        sorted(
            store.of_patient(patient_ref),
            key=lambda g: (g.granted_at, g.grant_ref),
            reverse=True,
        )
    )


def grant_access(
    patient_ref: str,
    grantee_ref: str,
    scope: frozenset[ScopeItem],
    purpose: str,
    expires_at: datetime,
    store: AccessGrantStore,
    clock: Callable[[], datetime],
    new_grant_ref: Callable[[], str] = _new_grant_ref,
) -> AccessGrant:
    now = clock()
    if expires_at <= now:
        raise InvalidAccessGrant("expires_at must be in the future")
    grant = AccessGrant(
        grant_ref=new_grant_ref(),
        patient_ref=patient_ref,
        grantee_ref=grantee_ref,
        scope=scope,
        purpose=purpose,
        granted_at=now,
        expires_at=expires_at,
    )
    store.save(grant)
    return grant


def revoke_access_grant(
    patient_ref: str,
    grant_ref: str,
    store: AccessGrantStore,
    clock: Callable[[], datetime],
) -> AccessGrant:
    grant = store.get(grant_ref)
    if grant is None or grant.patient_ref != patient_ref:
        raise GrantNotFound()
    revoked = grant.revoked(clock())
    store.save(revoked)
    return revoked
