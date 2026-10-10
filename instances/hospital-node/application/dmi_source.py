from typing import Protocol

from domain.dmi import DmiDescriptor, DmiExtract, PatientIdentity


class DmiUnavailable(Exception):
    """The DMI could not be reached, or answered in a way the adapter cannot read.

    Distinct from an empty extract: an unknown patient is not an error."""


class DmiSource(Protocol):
    """This Hospital Node's own legacy DMI / HIS, as the Node needs it (HC-120).

    Owned by the Hospital Node and implemented only by the hospital-specific adapters in
    adapters/dmi/, inside this Node. Each hospital may have a different implementation,
    mapping, and configuration; no central service implements or calls this port.

    Read-only: the Node never writes to the DMI through it. Authorization is not checked
    here; the use cases that disclose records check it first, as for ClinicalRepository.
    """

    def describe(self) -> DmiDescriptor:
        """What this adapter connects to and which record types it supplies."""
        ...

    def extract_patient(self, patient: PatientIdentity) -> DmiExtract:
        """The patient's records as the DMI holds them now, mapped to the canonical
        model and stamped with `patient.patient_ref`; entries that cannot be mapped are
        listed as rejected. A patient the DMI does not know gives an empty extract.
        Raises DmiUnavailable when the DMI cannot answer."""
        ...
