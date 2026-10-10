"""MOCKED access grant store for the D2 demo (HC-115).

Persistence is OPEN (ADR-0003), so grants live in memory. At startup the store is seeded
from the fictional patient access grants in demo-data/access.json. Grants recorded or
revoked through the access grants API change only this process's copy: they are lost on
restart, never written back to demo-data/ or storage_dir, and never reach another node.
"""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock

from domain.access_grant import AccessGrant, InvalidAccessGrant
from domain.patient_history import ScopeItem

# demo-data uses camelCase scope names; the contract uses snake_case.
_FIXTURE_SCOPE = {
    "encounters": ScopeItem.ENCOUNTERS,
    "medications": ScopeItem.MEDICATIONS,
    "labReports": ScopeItem.LAB_REPORTS,
}


class AccessGrantFixtureError(RuntimeError):
    pass


class InMemoryAccessGrantStore:
    mocked = True

    def __init__(self, grants: tuple[AccessGrant, ...] = ()) -> None:
        self._grants = {g.grant_ref: g for g in grants}
        self._lock = Lock()

    @classmethod
    def load(cls, access_path: Path) -> "InMemoryAccessGrantStore":
        try:
            fixture = json.loads(access_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise AccessGrantFixtureError(
                f"Cannot read access grant fixture {access_path}: {error}"
            ) from error
        if fixture.get("fictional") is not True:
            raise AccessGrantFixtureError(f"{access_path} is not marked fictional.")
        try:
            return cls(tuple(_grant(g) for g in fixture["accessGrants"]))
        except (KeyError, TypeError, ValueError, InvalidAccessGrant) as error:
            raise AccessGrantFixtureError(
                f"Invalid access grant in {access_path}: {error!r}"
            ) from error

    def get(self, grant_ref: str) -> AccessGrant | None:
        with self._lock:
            return self._grants.get(grant_ref)

    def of_patient(self, patient_ref: str) -> tuple[AccessGrant, ...]:
        with self._lock:
            return tuple(
                g for g in self._grants.values() if g.patient_ref == patient_ref
            )

    def save(self, grant: AccessGrant) -> None:
        with self._lock:
            self._grants[grant.grant_ref] = grant


def _grant(g: dict) -> AccessGrant:
    return AccessGrant(
        grant_ref=g["id"],
        patient_ref=g["patientId"],
        grantee_ref=g["granteeId"],
        scope=frozenset(_FIXTURE_SCOPE[item] for item in g["scope"]),
        purpose=g["purpose"],
        granted_at=datetime.fromisoformat(g["grantedAt"]),
        expires_at=datetime.fromisoformat(g["expiresAt"]),
        revoked_at=(datetime.fromisoformat(g["revokedAt"]) if g["revokedAt"] else None),
        in_force=g["status"] == "active",
    )
