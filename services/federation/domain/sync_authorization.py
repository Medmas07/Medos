from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from domain.federated_query import ScopeItem


class DenialReason(StrEnum):
    NOT_FOUND = "not_found"
    NOT_APPROVED = "not_approved"
    NOT_YET_VALID = "not_yet_valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REQUESTER_MISMATCH = "requester_mismatch"
    PATIENT_MISMATCH = "patient_mismatch"
    SCOPE_EXCEEDED = "scope_exceeded"
    PURPOSE_MISMATCH = "purpose_mismatch"


@dataclass(frozen=True)
class SyncAuthorization:
    """A temporary synchronization authorization as confirmed by the Governance Node.

    Federation never widens it: it is used only if it still covers the request.
    """

    decision_ref: str
    target_organization_refs: frozenset[str]
    scope: frozenset[ScopeItem]
    purpose: str
    valid_until: datetime

    def __post_init__(self) -> None:
        if not self.target_organization_refs or not self.scope:
            raise ValueError(
                "An authorization names at least one target and one scope."
            )

    def denial_for(
        self, scope: frozenset[ScopeItem], purpose: str, now: datetime
    ) -> DenialReason | None:
        """Why this authorization does not cover the request, or None if it does."""
        if self.valid_until <= now:
            return DenialReason.EXPIRED
        if not scope <= self.scope:
            return DenialReason.SCOPE_EXCEEDED
        if purpose != self.purpose:
            return DenialReason.PURPOSE_MISMATCH
        return None
