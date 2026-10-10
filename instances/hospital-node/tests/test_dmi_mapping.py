from datetime import date, datetime, timedelta, timezone

import pytest

from adapters.dmi.mapping import (
    CodeMap,
    InvalidCodeMap,
    UnmappedCode,
    map_entry,
    source_ref,
)
from domain.clinical_record import Encounter, Medication, MedicationStatus
from domain.dmi import RecordType, RejectedEntry, RejectionReason

# A fictional hospital's mapping tables, as a hospital-specific adapter would load them.
TABLES = {
    "version": "2026-10-01",
    "source_offset": "+01:00",
    "record_ref_prefix": "dmi-a-",
    "tables": {
        "encounter_types": {"URG": "emergency", "CS": "consultation"},
        "medication_codes": {"GLU850": "MED-GLUCOREL"},
        "medication_statuses": {"EN COURS": "active", "ARRET": "stopped"},
        "lab_tests": {"HBA1C": "HbA1c"},
        "lab_flags": {"H": "high", "N": "normal", "B": "low"},
        "clinicians": {"MED-0042": "clin-x"},
    },
}
CODES = CodeMap.from_document(TABLES)
# A fictional legacy prescription, in the DMI's own shape and codes.
PRESCRIPTION = {
    "num_presc": 77812,
    "code_produit": "GLU850",
    "etat": "EN COURS",
    "date_debut": "2025-09-15",
    "posologie": "850 mg, 2 fois par jour",
    "prescripteur": "MED-0042",
}


def medication(entry: dict, patient_ref: str = "pat-b") -> Medication:
    """How an adapter builds a canonical record with the strategy's CodeMap."""
    prescriber = entry.get("prescripteur")
    return Medication(
        record_ref=CODES.record_ref(entry["num_presc"]),
        patient_ref=patient_ref,
        code=CODES.code("medication_codes", entry["code_produit"]),
        status=MedicationStatus(CODES.code("medication_statuses", entry["etat"])),
        start_date=date.fromisoformat(entry["date_debut"]),
        dosage=entry.get("posologie"),
        # An optional field that is present must map too; it is never dropped.
        prescribed_by_ref=prescriber and CODES.code("clinicians", prescriber),
    )


def mapped(entry: dict):
    return map_entry(
        lambda: medication(entry),
        source_ref(entry.get("num_presc"), "prescriptions", 0),
        RecordType.MEDICATIONS,
    )


def test_a_legacy_entry_maps_to_a_canonical_record():
    assert mapped(PRESCRIPTION) == Medication(
        record_ref="dmi-a-77812",
        patient_ref="pat-b",
        code="MED-GLUCOREL",
        status=MedicationStatus.ACTIVE,
        start_date=date(2025, 9, 15),
        dosage="850 mg, 2 fois par jour",
        prescribed_by_ref="clin-x",
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"code_produit": "GLU1000"}, RejectionReason.UNMAPPED_CODE),
        # Codes match exactly as the DMI writes them; nothing is case-folded or guessed.
        ({"etat": "en cours"}, RejectionReason.UNMAPPED_CODE),
        ({"prescripteur": "MED-9999"}, RejectionReason.UNMAPPED_CODE),
        ({"code_produit": None}, RejectionReason.UNMAPPED_CODE),
        ({"date_debut": "15/09/2025"}, RejectionReason.INVALID_VALUE),
        ({"num_presc": "77812 bis"}, RejectionReason.INVALID_VALUE),
    ],
)
def test_an_entry_that_cannot_map_completely_is_rejected_whole(changes, reason):
    assert mapped(PRESCRIPTION | changes) == RejectedEntry(
        "77812" if "num_presc" not in changes else "77812 bis",
        RecordType.MEDICATIONS,
        reason,
    )


def test_a_missing_required_field_is_rejected_by_position_when_the_id_is_missing():
    entry = {k: v for k, v in PRESCRIPTION.items() if k != "num_presc"}

    assert mapped(entry) == RejectedEntry(
        "prescriptions[0]", RecordType.MEDICATIONS, RejectionReason.MISSING_FIELD
    )


def test_a_timestamp_without_offset_is_in_the_dmis_declared_offset():
    assert CODES.timestamp("2024-03-09T22:40:00") == datetime(
        2024, 3, 9, 22, 40, tzinfo=timezone(timedelta(hours=1))
    )
    # One that carries its own offset keeps it.
    assert CODES.timestamp("2024-03-09T21:40:00+00:00").utcoffset() == timedelta(0)


def test_canonical_record_refs_are_stable_and_prefixed():
    assert CODES.record_ref(77812) == CODES.record_ref("77812") == "dmi-a-77812"
    for bad in (None, True, 1.5):
        with pytest.raises(TypeError):
            CODES.record_ref(bad)


def test_unlisted_codes_and_tables_raise_unmapped_code():
    for table, code in (("lab_tests", "GLY"), ("units", "g/L")):
        with pytest.raises(UnmappedCode):
            CODES.code(table, code)
    assert CODES.code("lab_flags", "B") == "low"


def test_a_canonical_value_the_model_refuses_rejects_the_entry():
    # The CodeMap gives "emergency"; the canonical model refuses the naive datetime.
    def encounter() -> Encounter:
        return Encounter(
            record_ref=CODES.record_ref("E1"),
            patient_ref="pat-a",
            type=CODES.code("encounter_types", "URG"),
            title="Consultation aux urgences",
            started_at=datetime(2024, 3, 9, 22, 40),
            clinician_ref=CODES.code("clinicians", "MED-0042"),
        )

    assert map_entry(encounter, "E1", RecordType.ENCOUNTERS) == RejectedEntry(
        "E1", RecordType.ENCOUNTERS, RejectionReason.INVALID_VALUE
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"version": " "},
        {"version": None},
        {"source_offset": "Africa/Tunis"},
        {"record_ref_prefix": "dmi a"},
        {"tables": {"units": {"g/L": "g/L"}}},
        {"tables": {"medication_statuses": {"SUSP": "suspended"}}},
        {"tables": {"lab_flags": {"HH": "critical"}}},
        {"tables": {"clinicians": {"MED-0042": "Dr. X"}}},
        {"tables": {"medication_codes": {"GLU850": ""}}},
        {"tables": []},
    ],
)
def test_a_mapping_table_with_any_unusable_part_is_refused(changes):
    with pytest.raises(InvalidCodeMap):
        CodeMap.from_document(TABLES | changes)


def test_a_mapping_table_document_must_be_complete():
    for missing in ("version", "source_offset", "record_ref_prefix", "tables"):
        with pytest.raises(InvalidCodeMap):
            CodeMap.from_document({k: v for k, v in TABLES.items() if k != missing})
    with pytest.raises(InvalidCodeMap):
        CodeMap.from_document([])


@pytest.mark.parametrize(
    ("entry_id", "expected"),
    [
        ("RX-1", "RX-1"),
        (77812, "77812"),
        ("", "rx[3]"),
        ("RX\n1", "rx[3]"),
        (None, "rx[3]"),
    ],
)
def test_a_rejection_names_the_dmi_id_or_the_position(entry_id, expected):
    assert source_ref(entry_id, "rx", 3) == expected
