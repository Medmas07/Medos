"""PatientGrantDirectory over the fictional grants of demo-data/access.json (HC-132).

MOCKED, opt-in only (GOVERNANCE_GRANTS=fixture). Patient access grants are recorded and
enforced by the Hospital Nodes (patient-access-grants.v1.yaml, HC-115); by default the
Governance Node asks them over HTTP (HttpPatientGrantDirectory, HC-136). This directory
reads the fictional seed grants instead, read-only, for demos without Hospital Nodes
running: it ignores which node holds a grant and never sees a grant recorded or revoked
on a Hospital Node at runtime.
"""

import json
from datetime import datetime
from pathlib import Path

from adapters.outbound.in_memory_synchronization import FIXTURE_SCOPE
from domain.synchronization import PatientGrant


class FixturePatientGrantDirectory:
    mode = "fixture"
    mocked = True

    def __init__(self, grants: list[PatientGrant]) -> None:
        self._grants = {g.grant_ref: g for g in grants}

    @classmethod
    def load(cls, path: Path) -> "FixturePatientGrantDirectory":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("fictional") is not True:
            raise RuntimeError(f"{path} is not marked fictional")
        return cls(
            [
                PatientGrant(
                    grant_ref=g["id"],
                    patient_ref=g["patientId"],
                    scope=frozenset(FIXTURE_SCOPE[item] for item in g["scope"]),
                    expires_at=datetime.fromisoformat(g["expiresAt"]),
                    revoked=g["status"] == "revoked" or g["revokedAt"] is not None,
                )
                for g in data["accessGrants"]
            ]
        )

    def grant(
        self, holder_organization_ref: str, patient_ref: str, grant_ref: str
    ) -> PatientGrant | None:
        # As a Hospital Node lists by patient: another patient's grant is not found.
        grant = self._grants.get(grant_ref)
        return grant if grant and grant.patient_ref == patient_ref else None
