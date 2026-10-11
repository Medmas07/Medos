"""SyncAuthorizationChecker over HTTP: contracts/federation/sync-authorization-check.v1.yaml.

Anything other than a well-formed answer from the Governance Node about the decision that
was asked counts as GovernanceUnavailable, so the caller denies by default.
"""

from datetime import datetime
from urllib.parse import quote

import httpx

from application.federate_patient_query import (
    GovernanceUnavailable,
    SyncAuthorizationDenied,
)
from domain.federated_query import Requester, ScopeItem
from domain.sync_authorization import DenialReason, SyncAuthorization

RESULT_FIELDS = {
    "decision_ref",
    "outcome",
    "reason",
    "target_organization_refs",
    "scope",
    "purpose",
    "valid_until",
    "checked_at",
}
# Since sync-authorization-check 1.2.0 (HC-214); absent from a 1.1 Governance Node.
SIGNED_FIELD = "signed_authorization"


class HttpSyncAuthorizationChecker:
    def __init__(
        self, governance_url: str, timeout_seconds: float = 2.0, transport=None
    ) -> None:
        self._governance_url = governance_url.rstrip("/")
        self._timeout = timeout_seconds
        self._transport = transport

    def check(
        self,
        decision_ref: str,
        requested_by: Requester,
        patient_ref: str,
        scope: frozenset[ScopeItem],
        purpose: str,
    ) -> SyncAuthorization:
        url = (
            f"{self._governance_url}/v1/synchronization-authorizations/"
            f"{quote(decision_ref, safe='')}/checks"
        )
        body = {
            "requester_organization_ref": requested_by.organization_ref,
            "actor_ref": requested_by.actor_ref,
            "patient_ref": patient_ref,
            "scope": sorted(item.value for item in scope),
            "purpose": purpose,
        }
        try:
            with httpx.Client(
                timeout=self._timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = client.post(url, json=body)
        except httpx.HTTPError as error:
            raise GovernanceUnavailable(
                "The Governance Node could not be reached."
            ) from error
        if response.status_code != 200:
            raise GovernanceUnavailable(
                f"The Governance Node answered HTTP {response.status_code}."
            )
        try:
            return _from_wire(decision_ref, response.json())
        except (ValueError, TypeError, KeyError) as error:
            raise GovernanceUnavailable(
                "The Governance Node answered outside the contract."
            ) from error


def _from_wire(decision_ref: str, result: object) -> SyncAuthorization:
    if not isinstance(result, dict) or set(result) - {SIGNED_FIELD} != RESULT_FIELDS:
        raise ValueError("not a CheckResult")
    signed = result.get(SIGNED_FIELD)
    if signed is not None and not isinstance(signed, str):
        raise ValueError("invalid signed authorization")
    if result["decision_ref"] != decision_ref:
        raise ValueError("answer for another decision")
    if result["outcome"] == "denied":
        raise SyncAuthorizationDenied(DenialReason(result["reason"]))
    if result["outcome"] != "authorized" or result["reason"] is not None:
        raise ValueError("unknown outcome")
    targets = result["target_organization_refs"]
    scope = result["scope"]
    if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
        raise ValueError("invalid targets")
    if not isinstance(scope, list) or not isinstance(result["purpose"], str):
        raise ValueError("invalid scope or purpose")
    valid_until = datetime.fromisoformat(result["valid_until"])
    if valid_until.tzinfo is None:
        raise ValueError("valid_until has no offset")
    return SyncAuthorization(
        decision_ref=decision_ref,
        target_organization_refs=frozenset(targets),
        scope=frozenset(ScopeItem(item) for item in scope),
        purpose=result["purpose"],
        valid_until=valid_until,
        signed_authorization=signed,
    )
