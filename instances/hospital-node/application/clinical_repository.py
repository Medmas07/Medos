from typing import Protocol

from domain.clinical_record import PatientRecords, RepositorySummary


class ClinicalRepository(Protocol):
    """Clinical records held by this Hospital Node, and only by it.

    Authorization is not checked here: get_patient_history checks it before reading
    (HC-114).
    """

    def patient_records(self, patient_ref: str) -> PatientRecords:
        """Same empty answer for an unknown patient as for one with no records."""
        ...

    def summary(self) -> RepositorySummary: ...
