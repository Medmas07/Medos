"""A Governance-signed authorization, once its signature has been verified (HC-214).

The Governance Node attests, for a short time, exactly which exchange one of its
synchronization decisions authorizes (contracts/federation/sync-authorization-check.v1.yaml).
This node accepts a query under that decision only if the attestation comes from the
Authority it trusts, names this node's organization, and covers the query exactly. It
denies by default: anything missing, different, wider, early, or late is refused.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.patient_history import AuthorizationBasis, HistoryQuery, ScopeItem

# Tolerated difference between this node's clock and the Governance Node's, for the
# issue time only: an attestation is never accepted after it expires.
CLOCK_SKEW = timedelta(seconds=60)


@dataclass(frozen=True)
class SignedAuthorization:
    token_id: str
    issuer_ref: str
    decision_ref: str
    audience_refs: frozenset[str]
    requester_organization_ref: str
    actor_ref: str
    patient_ref: str
    scope: frozenset[ScopeItem]
    purpose: str
    issued_at: datetime
    expires_at: datetime

    def covers(
        self,
        query: HistoryQuery,
        trusted_issuer_ref: str,
        organization_ref: str,
        at: datetime,
    ) -> bool:
        return (
            self.issuer_ref == trusted_issuer_ref
            and organization_ref in self.audience_refs
            and query.authorization.basis is AuthorizationBasis.SYNCHRONIZATION_DECISION
            and query.authorization.ref == self.decision_ref
            and query.requested_by.organization_ref == self.requester_organization_ref
            and query.requested_by.actor_ref == self.actor_ref
            and query.patient_ref == self.patient_ref
            and query.purpose == self.purpose
            and query.scope <= self.scope
            and self.issued_at - CLOCK_SKEW <= at < self.expires_at
        )
