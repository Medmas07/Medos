"""Clinical records held by this Hospital Node (HC-113).

A minimal hospital-local model; its FHIR mapping is OPEN. Field names follow the record
shapes of contracts/federation/hospital-node-federation.v1.yaml so the APIs that disclose
these records translate them without renaming. Every record belongs to this node only.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from domain.node_identity import is_opaque_ref


class InvalidClinicalRecord(ValueError):
    pass


class MedicationStatus(Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class LabFlag(Enum):
    """Flag as assigned at the source; this node does not interpret results."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


def _require_refs(record: object, *fields: str) -> None:
    for field in fields:
        value = getattr(record, field)
        if value is not None and not is_opaque_ref(value):
            raise InvalidClinicalRecord(f"{field} must be an opaque reference")


def _require_aware(field: str, value: datetime) -> None:
    if value.tzinfo is None:
        raise InvalidClinicalRecord(f"{field} must include a UTC offset")


@dataclass(frozen=True)
class Encounter:
    record_ref: str
    patient_ref: str
    type: str
    title: str
    started_at: datetime
    clinician_ref: str
    reason: str | None = None
    summary: str | None = None

    def __post_init__(self) -> None:
        _require_refs(self, "record_ref", "patient_ref", "clinician_ref")
        _require_aware("started_at", self.started_at)


@dataclass(frozen=True)
class Medication:
    record_ref: str
    patient_ref: str
    code: str
    status: MedicationStatus
    start_date: date
    end_date: date | None = None
    dosage: str | None = None
    prescribed_by_ref: str | None = None
    encounter_ref: str | None = None

    def __post_init__(self) -> None:
        _require_refs(
            self, "record_ref", "patient_ref", "prescribed_by_ref", "encounter_ref"
        )


@dataclass(frozen=True)
class ReferenceRange:
    low: float
    high: float


@dataclass(frozen=True)
class LabResult:
    test: str
    value: float
    unit: str
    flag: LabFlag
    reference_range: ReferenceRange | None = None


@dataclass(frozen=True)
class LabReport:
    record_ref: str
    patient_ref: str
    title: str
    collected_at: datetime
    results: tuple[LabResult, ...]
    encounter_ref: str | None = None

    def __post_init__(self) -> None:
        _require_refs(self, "record_ref", "patient_ref", "encounter_ref")
        _require_aware("collected_at", self.collected_at)


@dataclass(frozen=True)
class PatientRecords:
    """One patient's records held by this node. Empty for a patient it does not know."""

    encounters: tuple[Encounter, ...] = ()
    medications: tuple[Medication, ...] = ()
    lab_reports: tuple[LabReport, ...] = ()


@dataclass(frozen=True)
class RepositorySummary:
    """Record counts only, never patient data."""

    mocked: bool
    encounters: int
    medications: int
    lab_reports: int
