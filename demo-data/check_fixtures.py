"""Integrity checks for the canonical demo fixtures (HC-005).

Standard library only. Run from the repository root:

    python demo-data/check_fixtures.py

Pass ``--print-proof-hashes`` to print the expected hash of each simulated
ledger proof after editing an anchored payload. Exits with status 1 and lists every problem
when a check fails.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Keys that end in "Id" but hold an identifier value rather than a reference.
NON_REFERENCE_KEYS = {"federatedId"}

# Keys whose string values are ISO 8601 date-times or dates.
DATETIME_SUFFIXES = ("At",)
DATE_KEYS = {"birthDate", "startDate", "endDate", "referenceDate"}

# The only fields a simulated ledger proof may anchor (see AGENTS.md blockchain rules).
# research-authorization-check.v1.yaml variable names.
VARIABLE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,99}")
ALLOWED_PROOF_FIELDS = {"eventId", "decisionId", "outcome", "decidedAt", "organizationIds", "version"}

RECORD_COLLECTIONS = ("encounters", "medications", "labReports")


def load(relative: str) -> dict:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def proof_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def walk(node, path: str = ""):
    """Yields (path, key, value) for every key of every object in a JSON tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield path, key, value
            yield from walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, f"{path}[{index}]")


def collect_ids(name: str, node, ids: dict[str, str], errors: list[str]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("id"), str):
            if node["id"] in ids:
                errors.append(f"duplicate id {node['id']!r} in {name} and {ids[node['id']]}")
            ids[node["id"]] = name
        for value in node.values():
            collect_ids(name, value, ids, errors)
    elif isinstance(node, list):
        for value in node:
            collect_ids(name, value, ids, errors)


def check(print_proof_hashes: bool = False) -> list[str]:
    errors: list[str] = []
    manifest = load("manifest.json")
    files = {name: load(name) for name in manifest["files"]}
    files["manifest.json"] = manifest

    # Every file is explicitly marked fictional.
    for name, data in files.items():
        if data.get("fictional") is not True or not data.get("notice"):
            errors.append(f"{name}: missing 'fictional: true' or 'notice'")

    # Globally unique ids.
    ids: dict[str, str] = {}
    for name, data in files.items():
        collect_ids(name, data, ids, errors)

    catalog = {m["code"]: m for m in files["medication-rules.json"]["medications"]}
    for code, medication in catalog.items():
        if medication.get("fictional") is not True:
            errors.append(f"medication {code} is not marked fictional")

    # References, medication codes, and date formats.
    for name, data in files.items():
        for path, key, value in walk(data):
            where = f"{name}{path}.{key}"
            if key.endswith("Id") and key not in NON_REFERENCE_KEYS and value is not None:
                if value not in ids:
                    errors.append(f"{where}: unknown reference {value!r}")
            elif key.endswith("Ids") and isinstance(value, list):
                errors.extend(f"{where}: unknown reference {v!r}" for v in value if v not in ids)
            elif key == "medicationCode" and value not in catalog:
                errors.append(f"{where}: unknown medication code {value!r}")
            elif key == "medicationCodes":
                errors.extend(f"{where}: unknown medication code {v!r}" for v in value if v not in catalog)
            if isinstance(value, str) and (key.endswith(DATETIME_SUFFIXES) or key in DATE_KEYS):
                try:
                    if key in DATE_KEYS:
                        date.fromisoformat(value)
                    else:
                        parsed = datetime.fromisoformat(value)
                        if parsed.tzinfo is None:
                            errors.append(f"{where}: date-time {value!r} has no UTC offset")
                except ValueError:
                    errors.append(f"{where}: invalid date {value!r}")

    for role, target in manifest["scenarioRoles"].items():
        if target not in ids and target not in catalog:
            errors.append(f"manifest scenarioRoles[{role!r}]: unknown {target!r}")

    people = files["people.json"]
    clinician_org = {c["id"]: c["organizationId"] for c in people["clinicians"]}
    organizations = {o["id"]: o for o in files["organizations.json"]["organizations"]}

    # Each records file only holds records of its own organization, written by its own clinicians.
    records_by_patient: dict[str, set[str]] = {}
    active_meds: dict[str, set[str]] = {}
    for name in (n for n in manifest["files"] if n.startswith("records/")):
        data = files[name]
        holder = data["heldBy"]
        if not (organizations.get(holder) or {}).get("node"):
            errors.append(f"{name}: holder {holder!r} has no node to hold records")
        for collection in RECORD_COLLECTIONS:
            for record in data[collection]:
                records_by_patient.setdefault(record["patientId"], set()).add(holder)
                author = record.get("clinicianId") or record.get("prescribedById")
                if author and clinician_org.get(author) != holder:
                    errors.append(f"{name}: {record['id']} authored by {author!r} outside {holder}")
                if collection == "medications" and record["status"] == "active":
                    active_meds.setdefault(record["patientId"], set()).add(record["medicationCode"])

    # Simulated ledger proofs: minimized payload and matching hash.
    governance = files["governance.json"]
    for proof in governance["ledgerProofs"]:
        extra = set(proof["anchoredPayload"]) - ALLOWED_PROOF_FIELDS
        if extra:
            errors.append(f"{proof['id']}: forbidden anchored fields {sorted(extra)}")
        if proof.get("simulated") is not True:
            errors.append(f"{proof['id']}: must be marked simulated")
        expected = proof_hash(proof["anchoredPayload"])
        if print_proof_hashes:
            print(f"{proof['id']}: {expected}")
        if proof["hash"] != expected:
            errors.append(f"{proof['id']}: hash does not match anchored payload")

    # Research data scopes use the contract variable names, and an authorization only
    # narrows its request (contracts/api/research/, HC-133).
    projects = {p["id"]: p for p in files["research.json"]["projects"]}
    for project in projects.values():
        for variable in project["dataScope"]["variables"]:
            if not VARIABLE_NAME.fullmatch(variable):
                errors.append(f"{project['id']}: variable {variable!r} is not a contract name")
    requests = {r["id"]: r for r in governance["researchAccessRequests"]}
    for decision in governance["decisions"]:
        authorization = decision.get("researchAuthorization")
        if decision["subjectType"] != "research_access_request":
            if authorization:
                errors.append(f"{decision['id']}: research authorization on another subject")
            continue
        if (decision["outcome"] == "approved") != bool(authorization):
            errors.append(f"{decision['id']}: an approval, and only an approval, has a research authorization")
            continue
        if not authorization:
            continue
        project = projects[requests[decision["subjectId"]]["projectId"]]
        if not set(authorization["approvedOrganizationIds"]) <= set(project["participatingOrganizationIds"]):
            errors.append(f"{decision['id']}: authorizes an organization outside its project")
        if not set(authorization["approvedVariables"]) <= set(project["dataScope"]["variables"]):
            errors.append(f"{decision['id']}: authorizes a variable outside its project")
        if authorization["minimumCellSize"] < 10:
            errors.append(f"{decision['id']}: minimum cell size below the demo policy of 10")

    # Canonical scenario invariants (docs/planning/demo-scenario.md).
    roles = manifest["scenarioRoles"]
    patient_a, dr_x = roles["Patient A"], roles["Dr. X"]
    hospitals = [o for o in organizations.values() if o["type"] == "hospital"]
    if len(hospitals) < 3:
        errors.append("scenario: fewer than three hospitals")
    if len(people["patients"]) < 3:
        errors.append("scenario: fewer than three patients")
    if len(records_by_patient.get(patient_a, set())) < 3:
        errors.append("scenario: Patient A history does not span three organizations")
    medication_a, medication_b = roles["Medication A"], roles["Medication B"]
    if medication_a not in active_meds.get(patient_a, set()):
        errors.append("scenario: Patient A has no active Medication A")
    if not any(
        set(rule["medicationCodes"]) == {medication_a, medication_b}
        for rule in files["medication-rules.json"]["interactionRules"]
    ):
        errors.append("scenario: no deterministic rule for Medication A + Medication B")
    script = next(
        s for s in files["clinician.json"]["consultationScripts"]
        if s["id"] == roles["Consultation script (steps 7-14)"]
    )
    if script["plannedPrescription"]["medicationCode"] != medication_b or script["patientId"] != patient_a:
        errors.append("scenario: consultation script does not prescribe Medication B to Patient A")
    reference = datetime.fromisoformat(f"{manifest['referenceDate']}T12:00:00{manifest['utcOffset']}")
    if not any(
        g["patientId"] == patient_a and g["granteeId"] == dr_x and g["status"] == "active"
        and datetime.fromisoformat(g["expiresAt"]) > reference
        for g in files["access.json"]["accessGrants"]
    ):
        errors.append("scenario: no active grant from Patient A to Dr. X at the reference date")
    sync = next(s for s in governance["synchronizationRequests"] if s["id"] == roles["Synchronization request (step 20)"])
    if sync["status"] != "pending":
        errors.append("scenario: the step-20 synchronization request must start pending")

    return errors


def main() -> int:
    errors = check(print_proof_hashes="--print-proof-hashes" in sys.argv[1:])
    if errors:
        print(f"{len(errors)} problem(s) in demo-data:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("demo-data: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
