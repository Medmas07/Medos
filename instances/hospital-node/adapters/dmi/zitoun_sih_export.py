"""Hospital B's DMI adapter: its Zitoun SIH nightly export (HC-123).

A sample hospital-specific adapter. It implements the Node-owned DmiSource port
(application/dmi_source.py) for one hospital, HR Oued Zitoun, whose DMI (fictional, like
its export) has no real-time API and writes a JSON export each night. Everything about
that format stays here: French field names, `dd/mm/yyyy` dates without an offset,
decimal commas, local codes, and lab results as flat rows. Hospital B's mapping tables
and export location are its local configuration (config/hospital-b.dmi.json); another
hospital needs its own adapter or configuration.

Mapping follows the strategy of HC-122 (adapters/dmi/mapping.py): codes translate only
through Hospital B's CodeMap, each entry maps completely or is rejected whole by
reference and RejectionReason, and clinical content is carried as written.

- The configuration and its tables are read once, at construction: an adapter never maps
  with a table that cannot be used. The export is read on every extraction.
- An export that cannot be read, is not marked fictional, or comes from another
  establishment raises DmiUnavailable.
- `extracted_at` is when the DMI wrote the export, not when the Node read it: records
  are as of the last nightly export.

The DMI is simulated (describe() says `mocked`). Read-only; nothing is written back.
"""

import json
import re
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from adapters.dmi.mapping import CodeMap, InvalidCodeMap, map_entry, source_ref
from application.dmi_source import DmiUnavailable
from domain.clinical_record import (
    Encounter,
    LabFlag,
    LabReport,
    LabResult,
    Medication,
    MedicationStatus,
    PatientRecords,
    ReferenceRange,
)
from domain.dmi import (
    DmiDescriptor,
    DmiExtract,
    PatientIdentity,
    RecordType,
    RejectedEntry,
)

SYSTEM_NAME = "Zitoun SIH, export nocturne (logiciel fictif)"

# The export's date formats, read in the DMI's declared offset.
_DATE = "%d/%m/%Y"
_DATETIME = "%d/%m/%Y %H:%M"
# A number as the DMI writes it: decimal comma, no thousands separator.
_NUMBER = re.compile(r"-?\d+(,\d+)?")


class DmiConfigError(RuntimeError):
    """A local adapter configuration this adapter cannot run with."""


class _ConfigFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notice: str | None = None
    export_file: str = Field(min_length=1)
    # The DMI's own code for this establishment, written in every export.
    establishment_code: str = Field(min_length=1)
    # This hospital's mapping-table document (adapters/dmi/README.md).
    mapping: dict


class ZitounSihExportDmi:
    def __init__(
        self, export_path: Path, establishment_code: str, codes: CodeMap
    ) -> None:
        self._export_path = export_path
        self._establishment_code = establishment_code
        self._codes = codes

    @classmethod
    def from_config(cls, path: Path) -> "ZitounSihExportDmi":
        """Build the adapter from its local configuration; a relative export path is
        resolved against the configuration file."""
        try:
            raw = _ConfigFile.model_validate_json(path.read_text(encoding="utf-8"))
            codes = CodeMap.from_document(raw.mapping)
        except OSError as error:
            raise DmiConfigError(f"Cannot read {path}: {error}") from error
        except (ValidationError, InvalidCodeMap) as error:
            raise DmiConfigError(
                f"Invalid DMI configuration {path}: {error}"
            ) from error
        return cls(
            (path.parent / raw.export_file).resolve(), raw.establishment_code, codes
        )

    def describe(self) -> DmiDescriptor:
        return DmiDescriptor(SYSTEM_NAME, frozenset(RecordType), mocked=True)

    def extract_patient(self, patient: PatientIdentity) -> DmiExtract:
        export = self._read_export()
        try:
            exported_at = self._datetime(export["date_export"])
        except (KeyError, TypeError, ValueError) as error:
            raise DmiUnavailable(
                f"{self._export_path}: unreadable export date"
            ) from error

        ref = patient.patient_ref
        encounters, rejected_enc = _map(
            self._entries(export, "sejours", "num_sejour", patient),
            RecordType.ENCOUNTERS,
            lambda row: self._encounter(row, ref),
        )
        medications, rejected_rx = _map(
            self._entries(export, "prescriptions", "num_presc", patient),
            RecordType.MEDICATIONS,
            lambda row: self._medication(row, ref),
        )
        lab_reports, rejected_lab = _map(
            self._lab_report_entries(export, patient),
            RecordType.LAB_REPORTS,
            lambda rows: self._lab_report(rows, ref),
        )

        return DmiExtract(
            patient_ref=patient.patient_ref,
            records=PatientRecords(
                encounters=tuple(encounters),
                medications=tuple(medications),
                lab_reports=tuple(lab_reports),
            ),
            rejected=(*rejected_enc, *rejected_rx, *rejected_lab),
            extracted_at=exported_at,
        )

    def _read_export(self) -> dict:
        try:
            export = json.loads(self._export_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise DmiUnavailable(f"Cannot read {self._export_path}: {error}") from error
        if not isinstance(export, dict) or export.get("fictional") is not True:
            raise DmiUnavailable(f"{self._export_path} is not marked fictional.")
        if export.get("etablissement") != self._establishment_code:
            raise DmiUnavailable(
                f"{self._export_path} comes from {export.get('etablissement')!r}, "
                f"not {self._establishment_code!r}."
            )
        return export

    def _entries(
        self, export: dict, collection: str, id_field: str, patient: PatientIdentity
    ) -> list[tuple[str, dict]]:
        """This patient's rows, each with the reference a rejection would give it. A
        row without the patient's IPP (the DMI's local identifier) is not this
        patient's."""
        rows = export.get(collection)
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise DmiUnavailable(f"{self._export_path}: unreadable {collection}.")
        return [
            (source_ref(row.get(id_field), collection, position), row)
            for position, row in enumerate(rows)
            if row.get("ipp") == patient.local_identifier
        ]

    def _lab_report_entries(
        self, export: dict, patient: PatientIdentity
    ) -> list[tuple[str, list[dict]]]:
        """The export has one row per result; rows sharing a `num_demande` are one
        report, mapped or rejected whole. A row whose `num_demande` is unusable is a
        report of its own, rejected by position."""
        reports: dict[str, list[dict]] = {}
        for ref, row in self._entries(export, "resultats_bio", "num_demande", patient):
            reports.setdefault(ref, []).append(row)
        return list(reports.items())

    def _encounter(self, row: dict, patient_ref: str) -> Encounter:
        return Encounter(
            record_ref=self._codes.record_ref(row["num_sejour"]),
            patient_ref=patient_ref,
            type=self._codes.code("encounter_types", row["type_venue"]),
            title=_text(row["libelle"]),
            started_at=self._datetime(row["date_entree"]),
            clinician_ref=self._codes.code("clinicians", row["matricule_medecin"]),
            reason=_optional_text(row.get("motif")),
            summary=_optional_text(row.get("synthese")),
        )

    def _medication(self, row: dict, patient_ref: str) -> Medication:
        return Medication(
            record_ref=self._codes.record_ref(row["num_presc"]),
            patient_ref=patient_ref,
            code=self._codes.code("medication_codes", row["code_produit"]),
            status=MedicationStatus(
                self._codes.code("medication_statuses", row["etat"])
            ),
            start_date=_date(row["date_debut"]),
            end_date=_date(row["date_fin"]) if row.get("date_fin") else None,
            dosage=_optional_text(row.get("posologie")),
            # An optional field that is present must map too; it is never dropped.
            prescribed_by_ref=self._optional_code(
                "clinicians", row.get("prescripteur")
            ),
            encounter_ref=self._optional_ref(row.get("num_sejour")),
        )

    def _lab_report(self, rows: list[dict], patient_ref: str) -> LabReport:
        first = rows[0]
        # Report-level fields are repeated on every row; rows that disagree cannot
        # be one report.
        for field in ("num_sejour", "date_prelevement", "libelle_demande"):
            if any(row.get(field) != first.get(field) for row in rows):
                raise ValueError(f"rows of one report disagree on {field}")
        return LabReport(
            record_ref=self._codes.record_ref(first["num_demande"]),
            patient_ref=patient_ref,
            title=_text(first["libelle_demande"]),
            collected_at=self._datetime(first["date_prelevement"]),
            encounter_ref=self._optional_ref(first.get("num_sejour")),
            results=tuple(self._lab_result(row) for row in rows),
        )

    def _lab_result(self, row: dict) -> LabResult:
        low, high = row.get("borne_inf"), row.get("borne_sup")
        if bool(low) != bool(high):
            raise ValueError("a reference range needs both bounds")
        return LabResult(
            test=self._codes.code("lab_tests", row["code_analyse"]),
            value=_number(row["valeur"]),
            unit=_text(row["unite"]),
            # Flags come from the DMI; the Node never computes them from the range.
            flag=LabFlag(self._codes.code("lab_flags", row["indicateur"])),
            reference_range=(
                ReferenceRange(_number(low), _number(high)) if low else None
            ),
        )

    def _datetime(self, value: object) -> datetime:
        moment = datetime.strptime(_text(value), _DATETIME)
        return self._codes.timestamp(moment.isoformat())

    def _optional_code(self, table: str, value: object) -> str | None:
        return None if value in (None, "") else self._codes.code(table, value)

    def _optional_ref(self, value: object) -> str | None:
        return None if value in (None, "") else self._codes.record_ref(value)


def _map[T, R](
    entries: list[tuple[str, T]], kind: RecordType, build: Callable[[T], R]
) -> tuple[list[R], list[RejectedEntry]]:
    mapped, rejected = [], []
    for ref, entry in entries:
        result = map_entry(lambda: build(entry), ref, kind)
        (rejected if isinstance(result, RejectedEntry) else mapped).append(result)
    return mapped, rejected


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected non-empty text")
    return value


def _optional_text(value: object) -> str | None:
    return None if value in (None, "") else _text(value)


def _date(value: object) -> date:
    return datetime.strptime(_text(value), _DATE).date()


def _number(value: object) -> float:
    if not isinstance(value, str) or not _NUMBER.fullmatch(value):
        raise ValueError(f"not a DMI number: {value!r}")
    return float(value.replace(",", "."))
