"""A patient's grant of scoped, temporary access to one person (HC-115).

Recorded, listed, and revoked through
contracts/api/patient-access/patient-access-grants.v1.yaml, and cited as the basis
patient_access_grant of a patient history query, which this node enforces itself.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from domain.node_identity import is_opaque_ref
from domain.patient_history import HistoryQuery, ScopeItem


class InvalidAccessGrant(ValueError):
    pass


class GrantStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True)
class AccessGrant:
    grant_ref: str
    patient_ref: str
    grantee_ref: str
    scope: frozenset[ScopeItem]
    purpose: str
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    # False when the source already records the grant as no longer in force.
    in_force: bool = True

    def __post_init__(self) -> None:
        for field in ("grant_ref", "patient_ref", "grantee_ref"):
            if not is_opaque_ref(getattr(self, field)):
                raise InvalidAccessGrant(f"{field} must be an opaque reference")
        if not self.scope:
            raise InvalidAccessGrant("scope must name at least one record type")
        if not 1 <= len(self.purpose) <= 200 or not self.purpose.strip():
            raise InvalidAccessGrant("purpose must be 1 to 200 characters")
        times = (self.granted_at, self.expires_at, self.revoked_at)
        if any(t is not None and t.tzinfo is None for t in times):
            raise InvalidAccessGrant("grant times must include a UTC offset")
        if self.expires_at <= self.granted_at:
            raise InvalidAccessGrant("expires_at must be after granted_at")

    def status(self, at: datetime) -> GrantStatus:
        if self.revoked_at is not None:
            return GrantStatus.REVOKED
        if not self.in_force or self.expires_at <= at:
            return GrantStatus.EXPIRED
        return GrantStatus.ACTIVE

    def revoked(self, at: datetime) -> "AccessGrant":
        """Revocation is recorded, never a deletion; a second one keeps the first time."""
        return self if self.revoked_at is not None else replace(self, revoked_at=at)

    def allows(self, query: HistoryQuery, at: datetime) -> bool:
        """Only its grantee, for this patient and purpose, inside its scope, while active.

        The node trusts its own copy of the grant, never the expiry stated in the query.
        """
        return (
            self.status(at) is GrantStatus.ACTIVE
            and self.patient_ref == query.patient_ref
            and self.grantee_ref == query.requested_by.actor_ref
            and self.purpose == query.purpose
            and query.scope <= self.scope
        )
