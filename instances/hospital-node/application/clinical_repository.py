from typing import Protocol

from domain.clinical_record import PatientRecords, RepositorySummary


class ClinicalRepository(Protocol):
    """Clinical records held by this Hospital Node, and only by it.

    Authorization is not checked here: callers enforce consent and scope before they
    disclose anything (HC-114, HC-115).
    """

    def patient_records(self, patient_ref: str) -> PatientRecords:
        """Same empty answer for an unknown patient as for one with no records."""
        ...

    def summary(self) -> RepositorySummary: ...
