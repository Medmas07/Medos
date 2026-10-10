"""What every DMI adapter must do to implement the DmiSource port (HC-120).

Not a test module: adapter tests (HC-121, HC-123) call `check_dmi_source` with their
adapter, a patient its DMI knows, and one it does not. The checks are the port's
documented behavior, so every hospital-specific adapter is held to the same boundary.
"""

from application.dmi_source import DmiSource
from domain.dmi import DmiDescriptor, DmiExtract, PatientIdentity


def check_dmi_source(
    source: DmiSource, known: PatientIdentity, unknown: PatientIdentity
) -> DmiExtract:
    """Returns the known patient's extract for adapter-specific assertions."""
    descriptor = source.describe()
    assert isinstance(descriptor, DmiDescriptor)

    extract = source.extract_patient(known)
    assert isinstance(extract, DmiExtract)
    # Stamped with the ecosystem reference asked for, not the DMI's local identifier.
    assert extract.patient_ref == known.patient_ref
    # Only the record types the adapter declares.
    assert extract.record_types() <= descriptor.record_types
    # Read-only and deterministic for the same DMI state.
    assert source.extract_patient(known) == extract

    # An unknown patient is an empty extract, not an error.
    empty = source.extract_patient(unknown)
    assert empty.patient_ref == unknown.patient_ref
    assert empty.records == type(empty.records)()
    assert empty.rejected == ()
    return extract
