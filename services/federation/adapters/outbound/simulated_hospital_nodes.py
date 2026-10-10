"""MOCKED Hospital Nodes and node registry for the D2 demo (HC-141).

There is no Hospital Node runtime yet, so each approved organization in demo-data/ is
simulated in process. Each simulated node reads only the records file its own
organization holds, and speaks the wire format of hospital-node-federation.v1.yaml.

This is not node-to-node exchange and not security:
- authorization is checked against the fictional grants and decisions in demo-data/,
  standing in for verification with the Governance Node (HC-144);
- the registry is organizations.json, standing in for the node registry (HC-142).
"""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from adapters.outbound.hospital_node_contract import entries_from_wire, query_to_wire
from application.federate_patient_query import (
    NodeDenied,
    NodeUnavailable,
    RegistryUnavailable,
)
from domain.federated_query import Entry, NodeQuery, NodeRef

DEMO_DATA = Path(__file__).resolve().parents[4] / "demo-data"

# demo-data uses camelCase scope names; the contract uses snake_case.
FIXTURE_SCOPE = {
    "encounters": "encounters",
    "medications": "medications",
    "labReports": "lab_reports",
}


def _load(demo_data: Path, name: str) -> dict:
    try:
        return json.loads((demo_data / name).read_text())
    except (OSError, ValueError) as error:
        raise RegistryUnavailable(f"Cannot read demo data {name}.") from error


class DemoNodeRegistry:
    """Approved organizations that run a node, from demo-data/organizations.json."""

    def __init__(self, demo_data: Path = DEMO_DATA) -> None:
        self._demo_data = demo_data

    def approved_nodes(self) -> tuple[NodeRef, ...]:
        organizations = _load(self._demo_data, "organizations.json")["organizations"]
        return tuple(
            NodeRef(organization_ref=o["id"], node_ref=o["node"]["id"])
            for o in organizations
            if o["governanceStatus"] == "approved" and o["node"]
        )


class SimulatedHospitalNode:
    """One Hospital Node answering POST /v1/federation/queries from its own records."""

    def __init__(
        self,
        organization: dict,
        records: dict,
        grants: dict[str, dict],
        decisions: dict[str, dict],
        sync_requests: dict[str, dict],
        utc_offset: str,
        clock: Callable[[], datetime],
    ) -> None:
        self.organization_ref = organization["id"]
        self.node_ref = organization["node"]["id"]
        self._reachable = (
            organization["node"]["status"] == "online"
            and organization["node"]["dmiState"] == "connected"
        )
        self._records = records
        self._grants = grants
        self._decisions = decisions
        self._sync_requests = sync_requests
        self._utc_offset = utc_offset
        self._clock = clock

    def handle(self, request: dict) -> tuple[int, dict]:
        if not self._reachable:
            return 503, self._problem(503, "Node unavailable", "node_unavailable")
        if not self._authorized(request):
            return 403, self._problem(
                403, "Federation query not authorized", "authorization_denied"
            )
        return 200, {
            "query_id": request["query_id"],
            "contract_version": "1.0",
            "node_ref": self.node_ref,
            "organization_ref": self.organization_ref,
            "patient_ref": request["patient_ref"],
            # Same answer for an unknown patient as for "nothing in scope".
            "entries": self._entries(request["patient_ref"], set(request["scope"])),
            "provenance": {"mocked": True, "answered_at": self._clock().isoformat()},
        }

    def _authorized(self, request: dict) -> bool:
        authorization = request["authorization"]
        scope = set(request["scope"])
        now = self._clock()
        if authorization["basis"] == "patient_access_grant":
            grant = self._grants.get(authorization["ref"])
            return bool(
                grant
                and grant["status"] == "active"
                and grant["revokedAt"] is None
                and datetime.fromisoformat(grant["expiresAt"]) > now
                and grant["patientId"] == request["patient_ref"]
                and grant["granteeId"] == request["requested_by"]["actor_ref"]
                and grant["purpose"] == request["purpose"]
                and scope <= {FIXTURE_SCOPE[s] for s in grant["scope"]}
            )
        if authorization["basis"] == "synchronization_decision":
            decision = self._decisions.get(authorization["ref"])
            if not (
                decision
                and decision["subjectType"] == "synchronization_request"
                and decision["outcome"] == "approved"
                and decision["validUntil"]
                and datetime.fromisoformat(decision["validUntil"]) > now
            ):
                return False
            sync = self._sync_requests[decision["subjectId"]]
            return (
                sync["targetOrganizationId"] == self.organization_ref
                and sync["requesterOrganizationId"]
                == request["requested_by"]["organization_ref"]
                and sync["patientId"] == request["patient_ref"]
                and sync["purpose"] == request["purpose"]
                and scope <= {FIXTURE_SCOPE[s] for s in sync["scope"]}
            )
        return False

    def _entries(self, patient_ref: str, scope: set[str]) -> list[dict]:
        source = {"organization_ref": self.organization_ref, "node_ref": self.node_ref}
        entries = []
        if "encounters" in scope:
            for e in self._own(self._records["encounters"], patient_ref):
                encounter = {
                    "type": e["type"],
                    "title": e["title"],
                    "clinician_ref": e["clinicianId"],
                }
                encounter |= {k: e[k] for k in ("reason", "summary") if e.get(k)}
                entries.append(
                    self._entry(e["id"], "encounter", e["startedAt"], source, encounter)
                )
        if "medications" in scope:
            for m in self._own(self._records["medications"], patient_ref):
                medication = {
                    "code": m["medicationCode"],
                    "dosage": m["dosage"],
                    "status": m["status"],
                    "start_date": m["startDate"],
                    "end_date": m["endDate"],
                    "prescribed_by_ref": m["prescribedById"],
                }
                occurred_at = f"{m['startDate']}T00:00:00{self._utc_offset}"
                entries.append(
                    self._entry(m["id"], "medication", occurred_at, source, medication)
                )
        if "lab_reports" in scope:
            for r in self._own(self._records["labReports"], patient_ref):
                lab_report = {
                    "title": r["title"],
                    "results": [
                        {
                            "test": x["test"],
                            "value": x["value"],
                            "unit": x["unit"],
                            "reference_range": x["referenceRange"],
                            "flag": x["flag"],
                        }
                        for x in r["results"]
                    ],
                }
                entries.append(
                    self._entry(
                        r["id"], "lab_report", r["collectedAt"], source, lab_report
                    )
                )
        return entries

    def _own(self, records: list[dict], patient_ref: str) -> list[dict]:
        return [record for record in records if record["patientId"] == patient_ref]

    @staticmethod
    def _entry(entry_ref, record_type, occurred_at, source, details) -> dict:
        return {
            "entry_ref": entry_ref,
            "record_type": record_type,
            "occurred_at": occurred_at,
            "source": source,
            record_type: details,
        }

    @staticmethod
    def _problem(status: int, title: str, code: str) -> dict:
        return {"type": "about:blank", "title": title, "status": status, "code": code}


class SimulatedHospitalNodes:
    """HospitalNodeClient that routes each query to an in-process simulated node."""

    mocked = True

    def __init__(
        self, clock: Callable[[], datetime], demo_data: Path = DEMO_DATA
    ) -> None:
        manifest = _load(demo_data, "manifest.json")
        access = _load(demo_data, "access.json")
        governance = _load(demo_data, "governance.json")
        records_by_holder = {}
        for path in sorted((demo_data / "records").glob("*.json")):
            records = json.loads(path.read_text())
            records_by_holder[records["heldBy"]] = records
        self.nodes = {
            o["id"]: SimulatedHospitalNode(
                organization=o,
                records=records_by_holder[o["id"]],
                grants={g["id"]: g for g in access["accessGrants"]},
                decisions={d["id"]: d for d in governance["decisions"]},
                sync_requests={
                    s["id"]: s for s in governance["synchronizationRequests"]
                },
                utc_offset=manifest["utcOffset"],
                clock=clock,
            )
            for o in _load(demo_data, "organizations.json")["organizations"]
            if o["node"] and o["id"] in records_by_holder
        }

    def query(self, node: NodeRef, query: NodeQuery) -> tuple[Entry, ...]:
        simulated = self.nodes.get(node.organization_ref)
        if simulated is None or simulated.node_ref != node.node_ref:
            raise NodeUnavailable(f"No node {node.node_ref} is running.")
        status, body = simulated.handle(query_to_wire(query))
        if status == 403:
            raise NodeDenied(body["code"])
        if status != 200:
            raise NodeUnavailable(body["code"])
        return entries_from_wire(node, body)
