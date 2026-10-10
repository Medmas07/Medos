# Hospital-Local DMI / HIS Adapter

## Purpose and status

Hospital Node infrastructure-adapter boundary for its own legacy DMI/HIS. The **port is DEFINED** (HC-120, D1): the Node-owned `DmiSource` port and the values it returns exist, with tests. One adapter implements it: the **MOCKED local DMI adapter** (HC-121, D2), over a simulated DMI built from fictional demo data. **No real DMI is connected and nothing calls the port at runtime:** the Node still serves its records from its MOCKED fixture repository (HC-113). The mapping strategy is HC-122; a sample hospital-specific adapter is HC-123.

```text
Legacy DMI / HIS
        |
Hospital-specific DMI Adapter          <- adapters/dmi/ (this directory): one per hospital
        |   implements DmiSource
        v
DmiSource port                         <- application/dmi_source.py (owned by the Node)
        |   returns DmiExtract
        v
Hospital Node canonical clinical model <- domain/clinical_record.py, domain/dmi.py
        |
FHIR / internal clinical representation  (FHIR mapping OPEN)
```

Each hospital may require a different adapter implementation, mapping, and local configuration. A central service must never connect directly to every hospital DMI; only the corresponding Hospital Node owns and operates this integration boundary.

## The port (HC-120)

Following [ADR-0003](../../../../docs/decisions/ADR-0003-backend-runtime-strategy.md), the port is a `typing.Protocol` owned by the application layer, and the adapters live here. Earlier wording of this README suggested a `ports/` folder inside this directory; ADR-0003 places ports in `application/`, so the port lives there.

| Element | Where | What it is |
|---|---|---|
| `DmiSource` | [`application/dmi_source.py`](../../application/dmi_source.py) | `describe() -> DmiDescriptor` and `extract_patient(PatientIdentity) -> DmiExtract`. Read-only. |
| `DmiUnavailable` | same | Raised when the DMI cannot answer or answers in a way the adapter cannot read. |
| `PatientIdentity` | [`domain/dmi.py`](../../domain/dmi.py) | The DMI's local identifier (for example Hospital A's `BEN-2024-08812` for Patient A, [`people.json`](../../../../demo-data/people.json)) and the ecosystem `patient_ref` the records must carry. |
| `DmiDescriptor` | same | The system's display name, the record types the adapter supplies (`encounters`, `medications`, `lab_reports`), and `mocked`. No address or credential. |
| `DmiExtract` | same | One patient's records in the canonical model (`PatientRecords`), the entries the adapter could not map (`RejectedEntry`), and `extracted_at`. |
| `RejectedEntry` | same | A source entry left unmapped: its DMI-local reference, record type, and a reason code. Never its content. |

**Rules every adapter keeps:**

- **Canonical out, DMI in.** The adapter returns only canonical records. DMI formats, codes, and schemas stay inside it and never reach the Node's domain or any `contracts/` file.
- **One patient per extract.** Every record carries the `patient_ref` asked for, whatever identifier the DMI uses; a record of another patient makes the extract invalid.
- **Nothing dropped silently.** An entry that cannot be mapped is listed as rejected, so a partial import is visible. How rejected entries are reviewed is the mapping strategy's (HC-122).
- **Unknown is not an error.** A patient the DMI does not know gives an empty extract; only a DMI that cannot answer raises `DmiUnavailable`.
- **Declared types only.** An extract contains only the record types the descriptor declares.
- **Read-only, no authorization.** The Node never writes to the DMI through this port. Authorization is checked by the use cases that disclose records, as for `ClinicalRepository`.

**Conformance.** [`tests/dmi_port_contract.py`](../../tests/dmi_port_contract.py) checks these rules; each adapter's tests call `check_dmi_source(adapter, known, unknown)`. It runs against a test double ([`tests/test_dmi_port.py`](../../tests/test_dmi_port.py)), which is not an adapter, and against the mock local DMI adapter for each demo node ([`tests/test_mock_local_dmi.py`](../../tests/test_mock_local_dmi.py)).

**Not decided here, and OPEN or later tickets:** how the Node resolves a `patient_ref` to the DMI's local identifier (a Node-owned patient index), when extraction runs and where its results are stored (persistence is OPEN), the mapping and the reason-code vocabulary (HC-122), adapter configuration and credentials, incremental or event-driven synchronization, and writing back to the DMI. The port is internal to each Node: it is not a cross-component contract and has no file under `contracts/`.

## Mock local DMI adapter (HC-121)

MOCKED at D2. [`mock_local_dmi.py`](mock_local_dmi.py) implements `DmiSource` over a **simulated** DMI, never a real hospital system. It is built from three values: this hospital's fictional records file (the node's `mock_clinical_records`, for example [`demo-data/records/hospital-a.json`](../../../../demo-data/records/hospital-a.json)), the fictional [`people.json`](../../../../demo-data/people.json), and this node's `organization_ref`.

| Behavior | What the adapter does |
|---|---|
| `describe()` | `DMI local simulé (données fictives)`, all three record types, `mocked: true`. |
| Patient lookup | By the DMI's own local identifier only. The simulated DMI's patient index is the identifiers **this** organization gives patients in `people.json`; other organizations' identifiers are ignored, so Hospital A's `BEN-2024-08812` finds nothing on Hospital B. |
| Ecosystem reference | Every record returned is stamped with the `patient_ref` the Node asked for. Resolving it from the local identifier stays the Node's (OPEN). |
| Unknown patient | Empty extract. |
| Unreadable entry | Listed as rejected with its DMI id (or its position, such as `labReports[0]`, when the id is unusable) and a reason code: `missing_field` for a missing field, `invalid_value` for a value the canonical model refuses. Never its content. The patient's other records are still returned. These two codes are the adapter's own; the shared vocabulary is HC-122's. |
| Unavailable DMI | `DmiUnavailable` when either file cannot be read or parsed, is not marked `"fictional": true`, or the records file is held by another organization. Both files are read even for an unknown patient, so a DMI that cannot answer is never reported as not knowing the patient. |
| Freshness | Both files are read on every extraction, as a live DMI would be: an edit shows in the next extract. Constructing the adapter reads nothing, so a missing DMI would not stop a Node from starting. |
| `extracted_at` | The injected clock (UTC now by default). |

The simulated DMI keeps the demo-data **fixture shape**: entries are parsed by the same readers as the fixture repository (`adapters/outbound/fixture_clinical_repository.py`). That shape is not a legacy DMI format, so no DMI-to-canonical mapping happens here; legacy formats, local codes, and their mapping are HC-122 and HC-123.

Not done at D2: `main.py` does not build the adapter, and no configuration field names it. No use case calls the port, `/health` does not report the DMI, and the Node's records still come from the fixture repository. The demo data's disconnected private-practice DMI is not simulated here; it is shown only by the Federation Service's simulated nodes. There are no credentials, network calls, or writes.

Demo, from `instances/hospital-node/` with the virtual environment active (Hospital B; checked 2026-10-10):

```python
from pathlib import Path
from adapters.dmi.mock_local_dmi import MockLocalDmi
from domain.dmi import PatientIdentity

dmi = MockLocalDmi(Path("../../demo-data/records/hospital-b.json"),
                   Path("../../demo-data/people.json"), "org-hospital-b")
extract = dmi.extract_patient(PatientIdentity("pat-a", "OZ-55031"))
# enc-b-2026-leila, med-b-leila-coagulix, lab-b-2026-leila; rejected: ()
dmi.extract_patient(PatientIdentity("pat-a", "BEN-2024-08812"))  # empty: Hospital A's identifier
MockLocalDmi(Path("../../demo-data/records/hospital-a.json"),
             Path("../../demo-data/people.json"), "org-hospital-b").extract_patient(
    PatientIdentity("pat-a", "OZ-55031"))  # DmiUnavailable: held by 'org-hospital-a'
```

## Communication boundaries

The adapter implements the Hospital Node-owned `DmiSource` port. DMI representations must not leak into the Node Domain or repository-level cross-component contracts.

## Non-responsibilities

This is not a shared central integration service and does not define a universal hospital schema.

## Expected contents

The mock local adapter (HC-121) is here. Future tickets add a sample hospital-specific adapter (HC-123), with its mapping (HC-122) and local configuration. Each must pass the port conformance check and keep the Hospital Node's Clean/Hexagonal dependency direction.
