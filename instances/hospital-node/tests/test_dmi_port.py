"""The DmiSource port contract, exercised with a test double (HC-120).

The double stands for a hospital-specific adapter: it keys patients by the DMI's local
identifier (Hospital A's `BEN-2024-08812` for Patient A, demo-data/people.json) and
returns canonical records. It is not a DMI adapter; HC-121 delivers the first one.
"""

from datetime import datetime

import pytest

from application.dmi_source import DmiSource
from domain.clinical_record import PatientRecords
from domain.dmi import DmiDescriptor, DmiExtract, PatientIdentity, RecordType
from tests.dmi_port_contract import check_dmi_source
from tests.test_dmi import ENCOUNTER, REJECTED

AT = datetime.fromisoformat("2026-10-10T10:00:00+01:00")
PATIENT_A = PatientIdentity("pat-a", "BEN-2024-08812")
UNKNOWN = PatientIdentity("pat-z", "BEN-0000-00000")


class FakeDmi:
    """Test double at the DmiSource port, as Hospital A's adapter would answer."""

    def __init__(self, record_types=frozenset(RecordType)) -> None:
        self.record_types = record_types

    def describe(self) -> DmiDescriptor:
        return DmiDescriptor("Fictional DMI (test double)", self.record_types, True)

    def extract_patient(self, patient: PatientIdentity) -> DmiExtract:
        if patient.local_identifier != "BEN-2024-08812":
            return DmiExtract(patient.patient_ref, PatientRecords(), (), AT)
        return DmiExtract(
            patient.patient_ref,
            PatientRecords(encounters=(ENCOUNTER,)),
            (REJECTED,),
            AT,
        )


def test_a_conforming_adapter_passes_the_port_contract():
    source: DmiSource = FakeDmi()

    extract = check_dmi_source(source, PATIENT_A, UNKNOWN)

    assert extract.records.encounters == (ENCOUNTER,)
    assert extract.rejected == (REJECTED,)


def test_an_adapter_returning_undeclared_record_types_fails_it():
    encounters_only = FakeDmi(frozenset({RecordType.ENCOUNTERS}))

    # The double also rejects a medication entry, a type it does not declare.
    with pytest.raises(AssertionError):
        check_dmi_source(encounters_only, PATIENT_A, UNKNOWN)
