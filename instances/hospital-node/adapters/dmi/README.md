# Hospital-Local DMI / HIS Adapter

## Purpose and status

Hospital Node infrastructure-adapter boundary for its own legacy DMI/HIS. The **port is DEFINED** (HC-120, D1): the Node-owned `DmiSource` port and the values it returns exist, with tests. **No adapter exists yet:** no DMI is connected, nothing calls the port at runtime, and the Node still reads its MOCKED fixture repository (HC-113). The first adapter is a mock local DMI adapter (HC-121); the mapping strategy is HC-122; a sample hospital-specific adapter is HC-123.

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

**Conformance.** [`tests/dmi_port_contract.py`](../../tests/dmi_port_contract.py) checks these rules; each adapter's tests call `check_dmi_source(adapter, known, unknown)`. At D1 it runs only against a test double ([`tests/test_dmi_port.py`](../../tests/test_dmi_port.py)), which is not an adapter.

**Not decided here, and OPEN or later tickets:** how the Node resolves a `patient_ref` to the DMI's local identifier (a Node-owned patient index), when extraction runs and where its results are stored (persistence is OPEN), the mapping and the reason-code vocabulary (HC-122), adapter configuration and credentials, incremental or event-driven synchronization, and writing back to the DMI. The port is internal to each Node: it is not a cross-component contract and has no file under `contracts/`.

## Communication boundaries

The adapter implements the Hospital Node-owned `DmiSource` port. DMI representations must not leak into the Node Domain or repository-level cross-component contracts.

## Non-responsibilities

This is not a shared central integration service and does not define a universal hospital schema.

## Expected contents

Future tickets add the adapters here: a mock local adapter (HC-121) and a sample hospital-specific adapter (HC-123), with their mappings (HC-122) and local configuration. Each must pass the port conformance check and keep the Hospital Node's Clean/Hexagonal dependency direction.
