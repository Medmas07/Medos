from dataclasses import replace
from datetime import datetime

import pytest

from domain.clinical_record import Encounter, PatientRecords
from domain.dmi import (
    DmiDescriptor,
    DmiExtract,
    InvalidDmiExtract,
    PatientIdentity,
    RecordType,
    RejectedEntry,
)

AT = datetime.fromisoformat("2026-10-10T10:00:00+01:00")
ENCOUNTER = Encounter(
    record_ref="enc-a-2024-leila-er",
    patient_ref="pat-a",
    type="emergency",
    title="Consultation aux urgences",
    started_at=datetime.fromisoformat("2024-03-09T22:40:00+01:00"),
    clinician_ref="clin-rania",
)
REJECTED = RejectedEntry("RX-77812", RecordType.MEDICATIONS, "unmapped_code")
EXTRACT = DmiExtract("pat-a", PatientRecords(encounters=(ENCOUNTER,)), (REJECTED,), AT)


def test_an_extract_lists_its_record_types_including_rejected_ones():
    assert EXTRACT.record_types() == {RecordType.ENCOUNTERS, RecordType.MEDICATIONS}
    assert DmiExtract("pat-a", PatientRecords(), (), AT).record_types() == set()


@pytest.mark.parametrize(
    "changes",
    [
        {"patient_ref": "pat b"},
        {"extracted_at": datetime(2026, 10, 10, 10)},
        # Every record belongs to the patient asked for.
        {"patient_ref": "pat-b"},
    ],
)
def test_invalid_extracts(changes):
    with pytest.raises(InvalidDmiExtract):
        replace(EXTRACT, **changes)


@pytest.mark.parametrize(
    "build",
    [
        lambda: RejectedEntry("", RecordType.MEDICATIONS, "unmapped_code"),
        lambda: RejectedEntry("RX-1\n", RecordType.MEDICATIONS, "unmapped_code"),
        lambda: RejectedEntry("RX-1", RecordType.MEDICATIONS, "Unmapped code"),
        lambda: DmiDescriptor(" ", frozenset({RecordType.ENCOUNTERS}), True),
        lambda: DmiDescriptor("Fictional DMI", frozenset(), True),
        lambda: PatientIdentity("pat a", "BEN-2024-08812"),
        lambda: PatientIdentity("pat-a", ""),
    ],
)
def test_invalid_values(build):
    with pytest.raises(InvalidDmiExtract):
        build()


def test_a_local_identifier_need_not_be_opaque():
    # The DMI's own identifier format is the hospital's, not the ecosystem's.
    assert PatientIdentity("pat-a", "BEN 2024/08812").local_identifier == (
        "BEN 2024/08812"
    )
