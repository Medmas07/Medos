from datetime import datetime
from typing import Protocol

from domain.patient_history import AuthorizationBasis, HistoryQuery
from domain.signed_authorization import SignedAuthorization


class AuthorizationVerifier(Protocol):
    """Decides whether a query's Governance-backed basis covers it.

    Implementations deny by default: an unknown, expired, revoked, mis-addressed, or
    narrower basis is refused.
    """

    def allows(self, query: HistoryQuery, at: datetime) -> bool: ...


class SignedAuthorizationReader(Protocol):
    """Verifies the Governance Node's signature on a signed authorization (HC-214).

    Returns what it attests, or None for anything not signed by the trusted key or not
    in the contract's format. Says nothing about whether it covers a query."""

    def read(self, token: str) -> SignedAuthorization | None: ...


class SignedDecisionVerifier:
    """HC-214: a synchronization decision counts only with a signed authorization from
    the trusted Governance Node that covers the query; this node checks it on its own,
    without asking the Governance Node. Other bases are left to `others`."""

    def __init__(
        self,
        reader: SignedAuthorizationReader,
        trusted_issuer_ref: str,
        organization_ref: str,
        others: AuthorizationVerifier,
    ) -> None:
        self._reader = reader
        self._trusted_issuer_ref = trusted_issuer_ref
        self._organization_ref = organization_ref
        self._others = others

    def allows(self, query: HistoryQuery, at: datetime) -> bool:
        if query.authorization.basis is not AuthorizationBasis.SYNCHRONIZATION_DECISION:
            return self._others.allows(query, at)
        if query.signed_authorization is None:
            return False
        attested = self._reader.read(query.signed_authorization)
        return attested is not None and attested.covers(
            query, self._trusted_issuer_ref, self._organization_ref, at
        )
