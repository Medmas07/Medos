from datetime import date, datetime, timedelta, timezone

import pytest

from domain.clinical_record import (
    Encounter,
    InvalidClinicalRecord,
    LabReport,
    Medication,
    MedicationStatus,
    PatientRecords,
)

AT = datetime(2026, 10, 10, 9, 0, tzinfo=timezone(timedelta(hours=1)))


def encounter(**overrides) -> Encounter:
    fields = {
        "record_ref": "enc-test",
        "patient_ref": "pat-test",
        "type": "consultation",
        "title": "Consultation",
        "started_at": AT,
        "clinician_ref": "clin-test",
    }
    return Encounter(**(fields | overrides))


def test_accepts_a_valid_record():
    assert encounter().patient_ref == "pat-test"


@pytest.mark.parametrize(
    "field", ["record_ref", "patient_ref", "clinician_ref"], ids=str
)
def test_rejects_a_reference_that_is_not_opaque(field):
    with pytest.raises(InvalidClinicalRecord, match=field):
        encounter(**{field: "Leïla Mansouri"})


def test_rejects_a_time_without_utc_offset():
    with pytest.raises(InvalidClinicalRecord, match="started_at"):
        encounter(started_at=AT.replace(tzinfo=None))

    with pytest.raises(InvalidClinicalRecord, match="collected_at"):
        LabReport("lab-test", "pat-test", "Bilan", AT.replace(tzinfo=None), ())


def test_optional_references_may_be_absent_but_not_invalid():
    medication = Medication(
        "med-test", "pat-test", "MED-TEST", MedicationStatus.ACTIVE, date(2026, 1, 1)
    )
    assert medication.prescribed_by_ref is None

    with pytest.raises(InvalidClinicalRecord, match="prescribed_by_ref"):
        Medication(
            "med-test",
            "pat-test",
            "MED-TEST",
            MedicationStatus.ACTIVE,
            date(2026, 1, 1),
            prescribed_by_ref="Dr X",
        )


def test_patient_records_default_to_empty():
    assert PatientRecords() == PatientRecords((), (), ())
