"""PatientGrantDirectory over the Hospital Nodes' access grants API (HC-136).

The default grant source. The Hospital Node of the organization holding the records is
the source of truth for a patient's grants (patient-access-grants.v1.yaml, HC-115): the
Governance Node asks it over real HTTP, `GET /v1/patients/{patient_ref}/access-grants`,
each time it evaluates a consent, and stores nothing. Each call is bounded by a timeout;
a node that is not configured, cannot be reached, answers an error, or answers outside
the contract raises GrantsUnavailable, and the consent fails (deny by default).

The node URLs come from a Governance-side directory file (GOVERNANCE_HOSPITAL_NODES,
hospital-nodes.demo.json by default). How the Governance Node discovers nodes in
production, and how the two authenticate each other, are OPEN. The demo Hospital Nodes'
grant stores are themselves MOCKED (in memory, seeded from fictional data): the
integration is real, the grants are fictional.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import httpx

from adapters.outbound.in_memory_hospital_applications import SeedError
from application.synchronization import GrantsUnavailable
from domain.synchronization import PatientGrant, ScopeItem

TIMEOUT_SECONDS = 2.0
_OPAQUE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def load_hospital_nodes(path: Path) -> dict[str, str]:
    """organization_ref -> base URL of its Hospital Node. An invalid file stops startup."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("fictional") is not True:
            raise SeedError(f"{path} is not marked fictional")
        nodes = {}
        for entry in data["nodes"]:
            organization, url = entry["organization_ref"], entry["base_url"]
            if not _OPAQUE_REF.fullmatch(organization) or organization in nodes:
                raise SeedError(f"{path}: invalid or repeated {organization!r}")
            if not re.fullmatch(r"https?://[^\s/?#]+(/[^\s?#]*)?", url):
                raise SeedError(f"{path}: invalid base_url {url!r}")
            nodes[organization] = url.rstrip("/")
        return nodes
    except SeedError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SeedError(f"Cannot load Hospital Nodes {path}: {error}") from error


class HttpPatientGrantDirectory:
    mode = "http"
    mocked = False

    def __init__(
        self,
        nodes: dict[str, str],
        timeout: float = TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._nodes = dict(nodes)
        self._timeout = timeout
        self._transport = transport

    def grant(
        self, holder_organization_ref: str, patient_ref: str, grant_ref: str
    ) -> PatientGrant | None:
        base_url = self._nodes.get(holder_organization_ref)
        if base_url is None:
            raise GrantsUnavailable(
                f"no Hospital Node is configured for {holder_organization_ref}."
            )
        url = f"{base_url}/v1/patients/{quote(patient_ref, safe='')}/access-grants"
        try:
            with httpx.Client(
                timeout=self._timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = client.get(url)
        except httpx.HTTPError as error:
            raise GrantsUnavailable(
                f"the Hospital Node of {holder_organization_ref} could not be reached."
            ) from error
        if response.status_code != 200:
            raise GrantsUnavailable(
                f"the Hospital Node of {holder_organization_ref} answered HTTP "
                f"{response.status_code}."
            )
        try:
            grants = _grants(response.json(), holder_organization_ref, patient_ref)
        except (ValueError, TypeError, KeyError) as error:
            raise GrantsUnavailable(
                f"the Hospital Node of {holder_organization_ref} answered outside the "
                "access grants contract."
            ) from error
        return grants.get(grant_ref)


def _grants(body: object, organization_ref: str, patient_ref: str) -> dict:
    if not isinstance(body, dict):
        raise ValueError("not an AccessGrantList")
    if body["organization_ref"] != organization_ref:
        raise ValueError("answer from another organization")
    if body["patient_ref"] != patient_ref or not isinstance(body["grants"], list):
        raise ValueError("answer for another patient")
    grants = {}
    for raw in body["grants"]:
        if raw["patient_ref"] != patient_ref:
            raise ValueError("a grant of another patient")
        expires_at = datetime.fromisoformat(raw["expires_at"])
        if expires_at.tzinfo is None:
            raise ValueError("expires_at without UTC offset")
        scope = raw["scope"]
        if not isinstance(scope, list) or not scope:
            raise ValueError("invalid scope")
        grants[raw["grant_ref"]] = PatientGrant(
            grant_ref=raw["grant_ref"],
            patient_ref=patient_ref,
            scope=frozenset(ScopeItem(item) for item in scope),
            expires_at=expires_at,
            # The Governance Node evaluates expiry at its own clock; a revocation is a
            # recorded fact.
            revoked=raw["status"] == "revoked" or raw["revoked_at"] is not None,
        )
    return grants
