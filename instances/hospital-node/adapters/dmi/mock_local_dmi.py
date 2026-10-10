"""MOCKED local DMI adapter for the D2 demo (HC-121).

Implements the Node-owned DmiSource port (application/dmi_source.py) over a simulated
DMI: this hospital's fictional records file in demo-data/records/, and its patient index,
the local identifiers this organization gives patients in demo-data/people.json. No real
DMI is connected, and describe() says `mocked`.

What it simulates of a real DMI:

- It knows patients only by its own local identifier (Hospital A's `BEN-2024-08812`).
  Every record is stamped with the `patient_ref` the Node asks for.
- It is read on every extraction, as a live DMI would be. A source that cannot be read,
  is not marked fictional, or is held by another organization raises DmiUnavailable;
  the Node does not need its DMI to construct the adapter.
- An entry it cannot read is listed as rejected, by reference and reason code
  (`missing_field`, `invalid_value`), and the patient's other records are still returned.

The simulated DMI keeps the demo-data fixture shape, which is not a real DMI format:
mapping a legacy format to the canonical model is HC-122, and a hospital-specific adapter
is HC-123. Read-only; nothing is written back.
"""

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from adapters.outbound.fixture_clinical_repository import (
    encounter_from_fixture,
    lab_report_from_fixture,
    medication_from_fixture,
)
from application.dmi_source import DmiUnavailable
from domain.clinical_record import PatientRecords
from domain.dmi import (
    DmiDescriptor,
    DmiExtract,
    PatientIdentity,
    RecordType,
    RejectedEntry,
)

SYSTEM_NAME = "DMI local simulé (données fictives)"

# Fixture collection, the record type it holds, and how one entry is read.
_COLLECTIONS = (
    ("encounters", RecordType.ENCOUNTERS, encounter_from_fixture),
    ("medications", RecordType.MEDICATIONS, medication_from_fixture),
    ("labReports", RecordType.LAB_REPORTS, lab_report_from_fixture),
)


def _now() -> datetime:
    return datetime.now(UTC)


class MockLocalDmi:
    def __init__(
        self,
        records_path: Path,
        people_path: Path,
        organization_ref: str,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._records_path = records_path
        self._people_path = people_path
        self._organization_ref = organization_ref
        self._clock = clock

    def describe(self) -> DmiDescriptor:
        return DmiDescriptor(SYSTEM_NAME, frozenset(RecordType), mocked=True)

    def extract_patient(self, patient: PatientIdentity) -> DmiExtract:
        # Both sources are read even for an unknown patient, so a DMI that cannot answer
        # is never mistaken for one that does not know the patient.
        index = self._patient_index()
        records = self._read(self._records_path)
        if records.get("heldBy") != self._organization_ref:
            raise DmiUnavailable(
                f"{self._records_path} is held by {records.get('heldBy')!r}, "
                f"not {self._organization_ref!r}."
            )
        dmi_patient = index.get(patient.local_identifier)

        found: dict[RecordType, list] = {kind: [] for _, kind, _ in _COLLECTIONS}
        rejected: list[RejectedEntry] = []
        for collection, kind, parse in _COLLECTIONS:
            entries = records.get(collection)
            if not isinstance(entries, list) or not all(
                isinstance(entry, dict) for entry in entries
            ):
                raise DmiUnavailable(f"{self._records_path}: unreadable {collection}.")
            for position, entry in enumerate(entries):
                # An entry without this patient's DMI id is not this patient's.
                if dmi_patient is None or entry.get("patientId") != dmi_patient:
                    continue
                try:
                    record = parse(entry)
                except KeyError:
                    reason = "missing_field"
                except (TypeError, ValueError):
                    reason = "invalid_value"
                else:
                    found[kind].append(replace(record, patient_ref=patient.patient_ref))
                    continue
                rejected.append(
                    RejectedEntry(
                        _source_ref(entry, collection, position), kind, reason
                    )
                )

        return DmiExtract(
            patient_ref=patient.patient_ref,
            records=PatientRecords(
                encounters=tuple(found[RecordType.ENCOUNTERS]),
                medications=tuple(found[RecordType.MEDICATIONS]),
                lab_reports=tuple(found[RecordType.LAB_REPORTS]),
            ),
            rejected=tuple(rejected),
            extracted_at=self._clock(),
        )

    def _patient_index(self) -> dict[str, str]:
        """This organization's local identifiers, to the id its records are filed under."""
        people = self._read(self._people_path)
        try:
            return {
                local["value"]: person["id"]
                for person in people["patients"]
                for local in person["localIdentifiers"]
                if local["organizationId"] == self._organization_ref
            }
        except (KeyError, TypeError) as error:
            raise DmiUnavailable(
                f"{self._people_path}: unreadable patient index: {error!r}"
            ) from error

    def _read(self, path: Path) -> dict:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise DmiUnavailable(f"Cannot read {path}: {error}") from error
        if not isinstance(document, dict) or document.get("fictional") is not True:
            raise DmiUnavailable(f"{path} is not marked fictional.")
        return document


def _source_ref(entry: dict, collection: str, position: int) -> str:
    """The entry's DMI id, or its position when the id itself is unusable."""
    ref = entry.get("id")
    if isinstance(ref, str) and 0 < len(ref) <= 128 and ref.isprintable():
        return ref
    return f"{collection}[{position}]"
