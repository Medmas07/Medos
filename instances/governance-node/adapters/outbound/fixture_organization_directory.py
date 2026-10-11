"""OrganizationDirectory over the fictional organizations of demo-data/organizations.json
(HC-213).

The institutions the Governance Node knows, with their type. Read once at startup; an
organization of an unknown type stops it. Whether a hospital is approved comes from the
Authority's decisions (HC-131), not from this file.
"""

import json
from pathlib import Path

from domain.organization_identity import Organization, OrganizationType


class FixtureOrganizationDirectory:
    def __init__(self, organizations: list[Organization]) -> None:
        self._organizations = {o.organization_ref: o for o in organizations}

    @classmethod
    def load(cls, path: Path) -> "FixtureOrganizationDirectory":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("fictional") is not True:
            raise RuntimeError(f"{path} is not marked fictional")
        try:
            organizations = [
                Organization(o["id"], OrganizationType(o["type"]))
                for o in data["organizations"]
            ]
        except (KeyError, ValueError) as error:
            raise RuntimeError(
                f"{path} has an invalid organization: {error}"
            ) from error
        return cls(organizations)

    def organization(self, organization_ref: str) -> Organization | None:
        return self._organizations.get(organization_ref)
