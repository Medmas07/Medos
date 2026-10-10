"""DMI-to-canonical mapping strategy (HC-122): what every DMI adapter maps with.

An adapter reads entries in its DMI's own format and builds canonical records
(domain/clinical_record.py) from them. This module holds the parts of that mapping
which are the same for every hospital; reading the DMI's format stays in each adapter.

- CodeMap: one hospital's explicit, versioned mapping tables, from the DMI's local codes
  to canonical values. A code is translated only if the table lists it exactly; nothing
  is guessed, case-folded, or suggested by AI, and an unlisted code is never passed
  through as is.
- map_entry: maps one entry completely or rejects it with a RejectionReason. An entry
  is never partly imported, and a rejection carries references only, never content.

The tables are local to each Hospital Node and never belong in domain/ or contracts/.
The canonical model is this Node's own; mapping it to FHIR is OPEN.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from domain.clinical_record import LabFlag, MedicationStatus
from domain.dmi import RecordType, RejectedEntry, RejectionReason
from domain.node_identity import is_opaque_ref


class InvalidCodeMap(ValueError):
    """A mapping table that cannot be used: the adapter must not map with it."""


class UnmappedCode(Exception):
    """A local code the hospital's mapping table does not list."""

    def __init__(self, table: str, code: object) -> None:
        super().__init__(f"{table}: no mapping for {code!r}")
        self.table = table


def _any(value: str) -> bool:
    return bool(value.strip())


# Each table, and the rule its canonical values must satisfy.
_TABLES: dict[str, Callable[[str], bool]] = {
    "encounter_types": _any,
    "medication_codes": _any,
    "medication_statuses": lambda v: v in {s.value for s in MedicationStatus},
    "lab_tests": _any,
    "lab_flags": lambda v: v in {f.value for f in LabFlag},
    "clinicians": is_opaque_ref,
}


@dataclass(frozen=True)
class CodeMap:
    """One hospital's mapping tables: DMI-local code -> canonical value."""

    version: str
    # The UTC offset the DMI writes timestamps in when they carry none. Fixed: a DMI
    # in a zone with daylight saving needs more than this (OPEN).
    source_offset: timezone
    # Prepended to the DMI's own entry ids to make record references, so a DMI id
    # (often a bare number) cannot collide with another hospital's.
    record_ref_prefix: str
    tables: Mapping[str, Mapping[str, str]]

    @classmethod
    def from_document(cls, document: object) -> "CodeMap":
        """Read a mapping-table document; refuse it whole if any part is unusable:

        {"version": "...", "source_offset": "+01:00", "record_ref_prefix": "...",
         "tables": {"medication_codes": {"<local code>": "<canonical value>"}, ...}}
        """
        try:
            version = document["version"]
            prefix = document["record_ref_prefix"]
            offset = datetime.strptime(document["source_offset"], "%z").tzinfo
            tables = document["tables"]
            if not (isinstance(version, str) and _any(version)):
                raise InvalidCodeMap("version must be a non-empty string")
            if not (isinstance(prefix, str) and is_opaque_ref(prefix)):
                raise InvalidCodeMap("record_ref_prefix must be an opaque reference")
            unknown = set(tables) - set(_TABLES)
            if unknown:
                raise InvalidCodeMap(f"unknown tables {sorted(unknown)}")
            for name, entries in tables.items():
                for local, canonical in entries.items():
                    if not (isinstance(canonical, str) and _TABLES[name](canonical)):
                        raise InvalidCodeMap(
                            f"{name}: {local!r} maps to a non-canonical value"
                        )
        except InvalidCodeMap:
            raise
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise InvalidCodeMap(f"unreadable mapping tables: {error!r}") from error
        return cls(
            version,
            offset,
            prefix,
            {name: dict(entries) for name, entries in tables.items()},
        )

    def code(self, table: str, local: object) -> str:
        """The canonical value for a local code. Raises UnmappedCode if unlisted."""
        canonical = self.tables.get(table, {}).get(local) if local is not None else None
        if canonical is None:
            raise UnmappedCode(table, local)
        return canonical

    def record_ref(self, local_id: object) -> str:
        """The record reference for a DMI entry id, stable across extractions. The
        canonical model refuses one that is not opaque (invalid_value)."""
        if not isinstance(local_id, str | int) or isinstance(local_id, bool):
            raise TypeError("an entry id must be a string or an integer")
        return f"{self.record_ref_prefix}{local_id}"

    def timestamp(self, value: str) -> datetime:
        """A DMI timestamp; one without an offset is in the DMI's declared offset,
        never the server's."""
        moment = datetime.fromisoformat(value)
        return moment if moment.tzinfo else moment.replace(tzinfo=self.source_offset)


def map_entry[T](
    build: Callable[[], T], source_ref: str, record_type: RecordType
) -> T | RejectedEntry:
    """The canonical record `build` makes from one entry, or the entry rejected."""
    try:
        return build()
    except UnmappedCode:
        reason = RejectionReason.UNMAPPED_CODE
    except KeyError:
        reason = RejectionReason.MISSING_FIELD
    except (TypeError, ValueError):
        # Includes InvalidClinicalRecord: the canonical model refused a value.
        reason = RejectionReason.INVALID_VALUE
    return RejectedEntry(source_ref, record_type, reason)


def source_ref(entry_id: object, collection: str, position: int) -> str:
    """The entry's DMI id for a rejection, or its position when the id is unusable."""
    if isinstance(entry_id, int) and not isinstance(entry_id, bool):
        entry_id = str(entry_id)
    if (
        isinstance(entry_id, str)
        and 0 < len(entry_id) <= 128
        and entry_id.isprintable()
    ):
        return entry_id
    return f"{collection}[{position}]"
