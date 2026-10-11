"""What a Hospital Node receives from its own legacy DMI / HIS (HC-120).

The values on the Node side of the DMI port (application/dmi_source.py): records in this
Node's canonical clinical model (domain/clinical_record.py), never in the DMI's own
format. The DMI's representations, codes, and schema stay inside the hospital-specific
adapter (adapters/dmi/); how they map to the canonical model is the mapping strategy
(HC-122, adapters/dmi/README.md).

Two rules hold for every adapter:

- One patient per extraction. Every record carries the ecosystem patient reference the
  Node asked for, whatever local identifier the DMI uses.
- Nothing is dropped silently. A source entry the adapter cannot map is listed as
  rejected, by its DMI-local reference and a RejectionReason, never with its content.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from domain.clinical_record import PatientRecords
from domain.node_identity import is_opaque_ref


class InvalidDmiExtract(ValueError):
    pass


class RecordType(Enum):
    """The canonical record types a DMI can supply, as the Federation contracts name them."""

    ENCOUNTERS = "encounters"
    MEDICATIONS = "medications"
    LAB_REPORTS = "lab_reports"


class RejectionReason(Enum):
    """Why a source entry was not mapped (HC-122). The same codes for every adapter."""

    # A field the canonical record needs is absent from the entry.
    MISSING_FIELD = "missing_field"
    # A field is present but the canonical model refuses it: a malformed date, a
    # reference that is not opaque, a value of the wrong type.
    INVALID_VALUE = "invalid_value"
    # A local code (medication, test, encounter type, status, flag, clinician) has no
    # entry in this hospital's mapping table. It is never passed through as is.
    UNMAPPED_CODE = "unmapped_code"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidDmiExtract(message)


@dataclass(frozen=True)
class PatientIdentity:
    """Who to extract: the DMI's local identifier, and the ecosystem reference the
    canonical records must carry. Resolving one from the other is the Node's (OPEN)."""

    patient_ref: str
    local_identifier: str

    def __post_init__(self) -> None:
        _require(is_opaque_ref(self.patient_ref), "patient_ref must be opaque")
        _require(
            0 < len(self.local_identifier) <= 128
            and self.local_identifier.isprintable(),
            "local_identifier must be 1-128 printable characters",
        )


@dataclass(frozen=True)
class DmiDescriptor:
    """What this Node's DMI adapter connects to. No credential or address."""

    system_name: str
    record_types: frozenset[RecordType]
    # True for a simulated DMI (fixtures): never a real hospital system.
    mocked: bool

    def __post_init__(self) -> None:
        _require(
            0 < len(self.system_name.strip()) <= 100,
            "system_name must be 1-100 characters",
        )
        _require(bool(self.record_types), "a DMI supplies at least one record type")


@dataclass(frozen=True)
class RejectedEntry:
    """A source entry the adapter could not map. References and a reason only."""

    source_ref: str
    record_type: RecordType
    reason: RejectionReason

    def __post_init__(self) -> None:
        _require(
            0 < len(self.source_ref) <= 128 and self.source_ref.isprintable(),
            "source_ref must be 1-128 printable characters",
        )
        _require(
            isinstance(self.reason, RejectionReason), "reason must be a RejectionReason"
        )


@dataclass(frozen=True)
class DmiExtract:
    """One patient's records as the DMI holds them now, in the canonical model."""

    patient_ref: str
    records: PatientRecords
    rejected: tuple[RejectedEntry, ...]
    extracted_at: datetime

    def __post_init__(self) -> None:
        _require(is_opaque_ref(self.patient_ref), "patient_ref must be opaque")
        _require(
            self.extracted_at.tzinfo is not None, "extracted_at needs a UTC offset"
        )
        for record in (
            *self.records.encounters,
            *self.records.medications,
            *self.records.lab_reports,
        ):
            _require(
                record.patient_ref == self.patient_ref,
                f"{record.record_ref} belongs to another patient",
            )

    def record_types(self) -> frozenset[RecordType]:
        """The record types this extract contains."""
        present = {
            RecordType.ENCOUNTERS: self.records.encounters,
            RecordType.MEDICATIONS: self.records.medications,
            RecordType.LAB_REPORTS: self.records.lab_reports,
        }
        return frozenset(kind for kind, records in present.items() if records) | {
            entry.record_type for entry in self.rejected
        }
