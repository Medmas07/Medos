"""MOCKED authorization verifier for the D2 demo (HC-114, HC-115).

How a node verifies a query's basis with the Governance Node is OPEN, and no Governance
Node runs yet. This verifier stands in for that check: at startup it reads the fictional
Governance decisions in demo-data/ and keeps them in memory, read-only. Patient access
grants are looked up in this node's access grant store (HC-115), so a grant recorded or
revoked through the access grants API counts at once. It applies the same rules as the
Federation Service's simulated nodes (HC-141).

The node trusts its own copy of each basis, never the expiry stated in the request.
This is not real authorization and not production security.
"""

import json
from datetime import datetime
from pathlib import Path

from application.manage_access_grants import AccessGrantStore
from domain.patient_history import AuthorizationBasis, HistoryQuery, ScopeItem

# demo-data uses camelCase scope names; the contract uses snake_case.
_FIXTURE_SCOPE = {
    "encounters": ScopeItem.ENCOUNTERS,
    "medications": ScopeItem.MEDICATIONS,
    "labReports": ScopeItem.LAB_REPORTS,
}


class AuthorizationFixtureError(RuntimeError):
    pass


class FixtureAuthorizationVerifier:
    mocked = True

    def __init__(
        self,
        organization_ref: str,
        grants: AccessGrantStore,
        decisions: dict[str, dict],
        sync_requests: dict[str, dict],
    ) -> None:
        self._organization_ref = organization_ref
        self._grants = grants
        self._decisions = decisions
        self._sync_requests = sync_requests

    @classmethod
    def load(
        cls, grants: AccessGrantStore, governance_path: Path, organization_ref: str
    ) -> "FixtureAuthorizationVerifier":
        governance = _read_fictional(governance_path)
        try:
            return cls(
                organization_ref,
                grants=grants,
                decisions={d["id"]: d for d in governance["decisions"]},
                sync_requests={
                    s["id"]: s for s in governance["synchronizationRequests"]
                },
            )
        except (KeyError, TypeError) as error:
            raise AuthorizationFixtureError(
                f"Invalid authorization fixture: {error!r}"
            ) from error

    def allows(self, query: HistoryQuery, at: datetime) -> bool:
        try:
            if query.authorization.basis is AuthorizationBasis.PATIENT_ACCESS_GRANT:
                return self._grant_allows(query, at)
            if query.authorization.basis is AuthorizationBasis.SYNCHRONIZATION_DECISION:
                return self._decision_allows(query, at)
        except (KeyError, TypeError, ValueError):
            pass
        return False

    def _grant_allows(self, query: HistoryQuery, at: datetime) -> bool:
        grant = self._grants.get(query.authorization.ref)
        return grant is not None and grant.allows(query, at)

    def _decision_allows(self, query: HistoryQuery, at: datetime) -> bool:
        decision = self._decisions.get(query.authorization.ref)
        if not (
            decision
            and decision["subjectType"] == "synchronization_request"
            and decision["outcome"] == "approved"
            and decision["validUntil"]
            and datetime.fromisoformat(decision["validUntil"]) > at
        ):
            return False
        sync = self._sync_requests[decision["subjectId"]]
        return (
            sync["targetOrganizationId"] == self._organization_ref
            and sync["requesterOrganizationId"] == query.requested_by.organization_ref
            and sync["patientId"] == query.patient_ref
            and sync["purpose"] == query.purpose
            and query.scope <= _scope(sync["scope"])
        )


def _scope(items: list[str]) -> frozenset[ScopeItem]:
    return frozenset(_FIXTURE_SCOPE[item] for item in items)


def _read_fictional(path: Path) -> dict:
    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AuthorizationFixtureError(
            f"Cannot read authorization fixture {path}: {error}"
        ) from error
    if fixture.get("fictional") is not True:
        raise AuthorizationFixtureError(f"{path} is not marked fictional.")
    return fixture
