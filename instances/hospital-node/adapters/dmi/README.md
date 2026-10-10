# Hospital-Local DMI / HIS Adapter

## Purpose and status

Hospital Node infrastructure-adapter boundary for its own legacy DMI/HIS. The **port is DEFINED** (HC-120, D1): the Node-owned `DmiSource` port and the values it returns exist, with tests. One adapter implements it: the **MOCKED local DMI adapter** (HC-121, D2), over a simulated DMI built from fictional demo data. The **mapping strategy is DEFINED and IMPLEMENTED at D2** (HC-122): a shared rejection vocabulary, and the code-mapping building blocks every hospital-specific adapter maps with, tested against fictional mapping tables. **No real DMI is connected, no hospital has mapping tables yet, and nothing calls the port at runtime:** the Node still serves its records from its MOCKED fixture repository (HC-113). A sample hospital-specific adapter is HC-123.

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
| `RejectedEntry` | same | A source entry left unmapped: its DMI-local reference, record type, and a `RejectionReason` (HC-122). Never its content. |

**Rules every adapter keeps:**

- **Canonical out, DMI in.** The adapter returns only canonical records. DMI formats, codes, and schemas stay inside it and never reach the Node's domain or any `contracts/` file.
- **One patient per extract.** Every record carries the `patient_ref` asked for, whatever identifier the DMI uses; a record of another patient makes the extract invalid.
- **Nothing dropped silently.** An entry that cannot be mapped is listed as rejected, so a partial import is visible. See the [mapping strategy](#mapping-strategy-hc-122) for the reasons and who reviews them.
- **Unknown is not an error.** A patient the DMI does not know gives an empty extract; only a DMI that cannot answer raises `DmiUnavailable`.
- **Declared types only.** An extract contains only the record types the descriptor declares.
- **Read-only, no authorization.** The Node never writes to the DMI through this port. Authorization is checked by the use cases that disclose records, as for `ClinicalRepository`.

**Conformance.** [`tests/dmi_port_contract.py`](../../tests/dmi_port_contract.py) checks these rules; each adapter's tests call `check_dmi_source(adapter, known, unknown)`. It runs against a test double ([`tests/test_dmi_port.py`](../../tests/test_dmi_port.py)), which is not an adapter, and against the mock local DMI adapter for each demo node ([`tests/test_mock_local_dmi.py`](../../tests/test_mock_local_dmi.py)).

**Not decided here, and OPEN or later tickets:** how the Node resolves a `patient_ref` to the DMI's local identifier (a Node-owned patient index), when extraction runs and where its results are stored (persistence is OPEN), adapter configuration and credentials, incremental or event-driven synchronization, and writing back to the DMI. The port is internal to each Node: it is not a cross-component contract and has no file under `contracts/`.

## Mock local DMI adapter (HC-121)

MOCKED at D2. [`mock_local_dmi.py`](mock_local_dmi.py) implements `DmiSource` over a **simulated** DMI, never a real hospital system. It is built from three values: this hospital's fictional records file (the node's `mock_clinical_records`, for example [`demo-data/records/hospital-a.json`](../../../../demo-data/records/hospital-a.json)), the fictional [`people.json`](../../../../demo-data/people.json), and this node's `organization_ref`.

| Behavior | What the adapter does |
|---|---|
| `describe()` | `DMI local simulé (données fictives)`, all three record types, `mocked: true`. |
| Patient lookup | By the DMI's own local identifier only. The simulated DMI's patient index is the identifiers **this** organization gives patients in `people.json`; other organizations' identifiers are ignored, so Hospital A's `BEN-2024-08812` finds nothing on Hospital B. |
| Ecosystem reference | Every record returned is stamped with the `patient_ref` the Node asked for. Resolving it from the local identifier stays the Node's (OPEN). |
| Unknown patient | Empty extract. |
| Unreadable entry | Rejected through the mapping strategy's `map_entry`, with its DMI id (or its position, such as `labReports[0]`, when the id is unusable) and `missing_field` or `invalid_value`. Never its content. The patient's other records are still returned. Its codes are already canonical, so it maps with no `CodeMap` and never gives `unmapped_code`. |
| Unavailable DMI | `DmiUnavailable` when either file cannot be read or parsed, is not marked `"fictional": true`, or the records file is held by another organization. Both files are read even for an unknown patient, so a DMI that cannot answer is never reported as not knowing the patient. |
| Freshness | Both files are read on every extraction, as a live DMI would be: an edit shows in the next extract. Constructing the adapter reads nothing, so a missing DMI would not stop a Node from starting. |
| `extracted_at` | The injected clock (UTC now by default). |

The simulated DMI keeps the demo-data **fixture shape**: entries are parsed by the same readers as the fixture repository (`adapters/outbound/fixture_clinical_repository.py`). That shape is not a legacy DMI format, so no code mapping happens here; a legacy format with local codes, and its hospital's mapping tables, are HC-123's.

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

## Mapping strategy (HC-122)

DEFINED and IMPLEMENTED at D2 as building blocks; no hospital-specific adapter uses them yet (HC-123). How every DMI adapter turns its DMI's entries into the Node's canonical records:

```text
DMI entry (local format, local codes)
   | 1. read      the entry's fields, in the DMI's own format          (each adapter)
   | 2. translate local codes through this hospital's CodeMap tables   (mapping.py)
   | 3. normalize timestamps to an explicit UTC offset, record refs    (mapping.py)
   | 4. validate  by building the canonical record                     (domain/clinical_record.py)
   v
canonical record, stamped with the patient_ref asked for
   -- or --
RejectedEntry(DMI-local ref, record type, RejectionReason)             (map_entry)
```

"Canonical" means this Node's model in [`domain/clinical_record.py`](../../domain/clinical_record.py), whose field names follow the Federation contract's record shapes. Mapping it to FHIR, and choosing standard terminologies (for medicines, tests, units), are OPEN ([open questions](../../../../docs/OPEN_QUESTIONS.md)); a FHIR step would come after this one and needs an ADR.

**Rules:**

1. **Mapping lives in the hospital's own adapter.** The DMI's format, codes, and mapping tables stay in `adapters/dmi/` and that hospital's configuration. They never reach `domain/`, the port, or `contracts/`, and no central service holds or applies them.
2. **Codes are translated only by explicit tables.** A `CodeMap` is one hospital's versioned mapping tables, from local code to canonical value. A code matches only exactly as the DMI writes it: no case folding, fuzzy matching, or AI suggestion, and an unlisted code is never passed through as is. Its tables are `encounter_types`, `medication_codes`, `medication_statuses`, `lab_tests`, `lab_flags`, and `clinicians`.
3. **A table is refused whole if any part is unusable.** A status or lab flag outside the canonical enumerations, a clinician reference that is not opaque, an empty value, an unknown table, an unreadable offset, or a missing version raises `InvalidCodeMap`: an adapter never maps with a partly valid table.
4. **An entry maps completely or is rejected whole.** `map_entry` builds the canonical record or returns a `RejectedEntry`; an entry is never partly imported. An optional field that is present must map too: an unknown prescriber rejects the prescription rather than dropping the prescriber, and one unmappable lab result rejects its whole report.
5. **Clinical content is carried, not interpreted.** Titles, reasons, summaries, dosages, values, units, and reference ranges pass through as the DMI holds them. Lab flags come from the DMI through `lab_flags`; the Node never computes them from ranges. There is no unit conversion (OPEN), and no AI or LLM step anywhere in the mapping.
6. **Timestamps get an explicit offset.** A DMI timestamp without one is read in the DMI's declared `source_offset` (for example `+01:00`), never the server's zone. The offset is fixed; a DMI in a zone with daylight saving needs more (OPEN).
7. **Record references are stable.** `record_ref_prefix` + the DMI's entry id, so the same entry gives the same reference on every extraction and a bare DMI number cannot collide with another hospital's. One that is not opaque is rejected (`invalid_value`).

**Rejection reasons** (`RejectionReason` in [`domain/dmi.py`](../../domain/dmi.py), the same for every adapter):

| Reason | When |
|---|---|
| `missing_field` | A field the canonical record needs is absent from the entry. |
| `invalid_value` | A field is present but the canonical model refuses it: a malformed date, a timestamp without an offset, a non-opaque reference, a value of the wrong type. |
| `unmapped_code` | A local code (including an empty one) is not listed in this hospital's table. |

A rejection carries the DMI-local reference (or the entry's position when its id is unusable), the record type, and the reason, never the entry's content. **Reviewing rejections is a hospital-local task:** the hospital's data steward fixes the entry in the DMI or adds the missing code to the hospital's table (a new table version), and the next extraction picks it up. No review screen, queue, or notification exists (PLANNED, not ticketed); extracts are not stored yet (persistence is OPEN).

**Mapping-table document** (the fictional example from [`tests/test_dmi_mapping.py`](../../tests/test_dmi_mapping.py)):

```json
{
  "version": "2026-10-01",
  "source_offset": "+01:00",
  "record_ref_prefix": "dmi-a-",
  "tables": {
    "encounter_types": {"URG": "emergency", "CS": "consultation"},
    "medication_codes": {"GLU850": "MED-GLUCOREL"},
    "medication_statuses": {"EN COURS": "active", "ARRET": "stopped"},
    "lab_tests": {"HBA1C": "HbA1c"},
    "lab_flags": {"H": "high", "N": "normal", "B": "low"},
    "clinicians": {"MED-0042": "clin-x"}
  }
}
```

**Building blocks** ([`mapping.py`](mapping.py)): `CodeMap.from_document()`, `CodeMap.code(table, local)` (raises `UnmappedCode`), `CodeMap.timestamp()`, `CodeMap.record_ref()`, `map_entry(build, source_ref, record_type)`, and `source_ref(entry_id, collection, position)`. The [mock local adapter](#mock-local-dmi-adapter-hc-121) rejects through `map_entry`; HC-123 adds a hospital-specific adapter that reads a legacy format and maps it with a `CodeMap`.

Not decided here: where a hospital's tables are stored and loaded from (with its adapter configuration, HC-123), recording the table version with stored extracts (persistence is OPEN), standard terminologies and FHIR (OPEN), unit conversion, and a review interface for rejections.

Demo, from `instances/hospital-node/` with the virtual environment active (checked 2026-10-10):

```python
from adapters.dmi.mapping import CodeMap, map_entry
from domain.dmi import RecordType
from tests.test_dmi_mapping import TABLES, PRESCRIPTION, medication

codes = CodeMap.from_document(TABLES)
map_entry(lambda: medication(PRESCRIPTION), "77812", RecordType.MEDICATIONS)
# Medication(record_ref='dmi-a-77812', code='MED-GLUCOREL', status=ACTIVE, prescribed_by_ref='clin-x', ...)
map_entry(lambda: medication(PRESCRIPTION | {"code_produit": "GLU1000"}), "77812",
          RecordType.MEDICATIONS)
# RejectedEntry(source_ref='77812', record_type=MEDICATIONS, reason=UNMAPPED_CODE)
codes.timestamp("2024-03-09T22:40:00")  # 2024-03-09 22:40:00+01:00
```

## Communication boundaries

The adapter implements the Hospital Node-owned `DmiSource` port. DMI representations must not leak into the Node Domain or repository-level cross-component contracts.

## Non-responsibilities

This is not a shared central integration service and does not define a universal hospital schema.

## Expected contents

The mock local adapter (HC-121) and the mapping strategy's building blocks (HC-122) are here. HC-123 adds a sample hospital-specific adapter, with its mapping tables and local configuration. Each must pass the port conformance check and keep the Hospital Node's Clean/Hexagonal dependency direction.
