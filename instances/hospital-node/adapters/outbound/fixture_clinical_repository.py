"""MOCKED clinical repository for the D2 demo (HC-113).

Persistence is OPEN (ADR-0003), so this node keeps its records in memory, read once at
startup from the single demo-data records file its configuration names. The file must be
fictional and held by this node's own organization: a node never loads another
hospital's records. Read-only; nothing is written back, and storage_dir stays unused.

This is not a DMI integration (HC-120+) and not real clinical storage.
"""

import json
from datetime import date, datetime
from pathlib import Path

from domain.clinical_record import (
    Encounter,
    InvalidClinicalRecord,
    LabFlag,
    LabReport,
    LabResult,
    Medication,
    MedicationStatus,
    PatientRecords,
    ReferenceRange,
    RepositorySummary,
)
from domain.research_execution import ResearchSubject


class ClinicalFixtureError(RuntimeError):
    pass


class FixtureClinicalRepository:
    mocked = True

    def __init__(
        self,
        encounters: tuple[Encounter, ...],
        medications: tuple[Medication, ...],
        lab_reports: tuple[LabReport, ...],
    ) -> None:
        self._encounters = encounters
        self._medications = medications
        self._lab_reports = lab_reports

    @classmethod
    def load(cls, path: Path, organization_ref: str) -> "FixtureClinicalRepository":
        try:
            fixture = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ClinicalFixtureError(
                f"Cannot read clinical fixture {path}: {error}"
            ) from error
        if fixture.get("fictional") is not True:
            raise ClinicalFixtureError(f"{path} is not marked fictional.")
        if fixture.get("heldBy") != organization_ref:
            raise ClinicalFixtureError(
                f"{path} is held by {fixture.get('heldBy')!r}, not {organization_ref!r}."
            )
        try:
            return cls(
                tuple(encounter_from_fixture(e) for e in fixture["encounters"]),
                tuple(medication_from_fixture(m) for m in fixture["medications"]),
                tuple(lab_report_from_fixture(r) for r in fixture["labReports"]),
            )
        except (KeyError, TypeError, ValueError, InvalidClinicalRecord) as error:
            raise ClinicalFixtureError(
                f"Invalid clinical fixture {path}: {error!r}"
            ) from error

    def patient_records(self, patient_ref: str) -> PatientRecords:
        return PatientRecords(
            encounters=_of(self._encounters, patient_ref),
            medications=_of(self._medications, patient_ref),
            lab_reports=_of(self._lab_reports, patient_ref),
        )

    def summary(self) -> RepositorySummary:
        return RepositorySummary(
            mocked=self.mocked,
            encounters=len(self._encounters),
            medications=len(self._medications),
            lab_reports=len(self._lab_reports),
        )

    def local_research_subjects(self) -> tuple[ResearchSubject, ...]:
        """Internal-only view; patient references never leave the executor."""
        patient_refs = {
            record.patient_ref
            for records in (self._encounters, self._medications, self._lab_reports)
            for record in records
        }
        return tuple(self._research_subject(ref) for ref in sorted(patient_refs))

    def _research_subject(self, patient_ref: str) -> ResearchSubject:
        records = self.patient_records(patient_ref)
        return ResearchSubject(
            patient_ref=patient_ref,
            encounter_dates=tuple(
                encounter.started_at.date() for encounter in records.encounters
            ),
            hba1c_values=tuple(
                result.value
                for report in records.lab_reports
                for result in report.results
                if result.test.casefold() == "hba1c"
            ),
        )


def _of(records, patient_ref: str) -> tuple:
    return tuple(r for r in records if r.patient_ref == patient_ref)


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def encounter_from_fixture(e: dict) -> Encounter:
    return Encounter(
        record_ref=e["id"],
        patient_ref=e["patientId"],
        type=e["type"],
        title=e["title"],
        started_at=datetime.fromisoformat(e["startedAt"]),
        clinician_ref=e["clinicianId"],
        reason=e.get("reason"),
        summary=e.get("summary"),
    )


def medication_from_fixture(m: dict) -> Medication:
    return Medication(
        record_ref=m["id"],
        patient_ref=m["patientId"],
        code=m["medicationCode"],
        status=MedicationStatus(m["status"]),
        start_date=date.fromisoformat(m["startDate"]),
        end_date=_optional_date(m.get("endDate")),
        dosage=m.get("dosage"),
        prescribed_by_ref=m.get("prescribedById"),
        encounter_ref=m.get("encounterId"),
    )


def lab_report_from_fixture(r: dict) -> LabReport:
    return LabReport(
        record_ref=r["id"],
        patient_ref=r["patientId"],
        title=r["title"],
        collected_at=datetime.fromisoformat(r["collectedAt"]),
        encounter_ref=r.get("encounterId"),
        results=tuple(
            LabResult(
                test=x["test"],
                value=x["value"],
                unit=x["unit"],
                flag=LabFlag(x["flag"]),
                reference_range=(
                    ReferenceRange(**x["referenceRange"])
                    if x.get("referenceRange")
                    else None
                ),
            )
            for x in r["results"]
        ),
    )
