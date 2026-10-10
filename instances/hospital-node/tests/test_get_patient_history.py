from datetime import date, datetime

import pytest

from application.get_patient_history import AuthorizationDenied, get_patient_history
from domain.clinical_record import (
    Encounter,
    LabReport,
    Medication,
    MedicationStatus,
    PatientRecords,
    RepositorySummary,
)
from domain.patient_history import (
    Authorization,
    AuthorizationBasis,
    HistoryQuery,
    InvalidHistoryQuery,
    Requester,
    ScopeItem,
)
from tests.conftest import DEMO_NOW

AT = datetime.fromisoformat("2026-01-01T09:00:00+01:00")
RECORDS = PatientRecords(
    encounters=(Encounter("enc-1", "pat-1", "consultation", "Suivi", AT, "clin-1"),),
    medications=(
        Medication(
            "med-1", "pat-1", "MED-1", MedicationStatus.ACTIVE, date(2026, 1, 1)
        ),
    ),
    lab_reports=(LabReport("lab-1", "pat-1", "Bilan", AT, results=()),),
)


def query(**changes) -> HistoryQuery:
    fields = {
        "query_id": "0b9f6c2e-3d41-4a8e-9f57-1c2d3e4f5a6b",
        "patient_ref": "pat-1",
        "scope": frozenset(ScopeItem),
        "purpose": "Consultation",
        "requested_by": Requester("org-1", "clin-1"),
        "authorization": Authorization(
            AuthorizationBasis.PATIENT_ACCESS_GRANT, "grant-1", DEMO_NOW
        ),
    }
    return HistoryQuery(**(fields | changes))


class StubRepository:
    def __init__(self) -> None:
        self.read = []

    def patient_records(self, patient_ref: str) -> PatientRecords:
        self.read.append(patient_ref)
        return RECORDS if patient_ref == "pat-1" else PatientRecords()

    def summary(self) -> RepositorySummary:
        return RepositorySummary(
            mocked=True, encounters=1, medications=1, lab_reports=1
        )


class StubVerifier:
    def __init__(self, allows: bool) -> None:
        self._allows = allows
        self.checked_at = None

    def allows(self, query: HistoryQuery, at: datetime) -> bool:
        self.checked_at = at
        return self._allows


def history(q: HistoryQuery, allows: bool = True, repository=None):
    return get_patient_history(
        q, repository or StubRepository(), StubVerifier(allows), lambda: DEMO_NOW
    )


def test_returns_the_records_inside_the_scope():
    result = history(query(scope=frozenset({ScopeItem.MEDICATIONS})))

    assert result.records == PatientRecords(medications=RECORDS.medications)
    assert (result.query_id, result.patient_ref) == (query().query_id, "pat-1")


def test_reports_mocked_provenance_and_answer_time():
    result = history(query())

    assert (result.mocked, result.answered_at) == (True, DEMO_NOW)


def test_unknown_patient_gets_an_empty_answer():
    assert history(query(patient_ref="pat-unknown")).records == PatientRecords()


def test_refusal_reads_no_record():
    repository = StubRepository()

    with pytest.raises(AuthorizationDenied):
        history(query(), allows=False, repository=repository)
    assert repository.read == []


def test_verifier_is_asked_at_the_clock_time():
    verifier = StubVerifier(True)

    get_patient_history(query(), StubRepository(), verifier, lambda: DEMO_NOW)

    assert verifier.checked_at == DEMO_NOW


@pytest.mark.parametrize(
    "changes",
    [
        {"patient_ref": "Patient A"},
        {"scope": frozenset()},
        {"purpose": "  "},
        {"requested_by": Requester("org-1", "clin x")},
        {
            "authorization": Authorization(
                AuthorizationBasis.PATIENT_ACCESS_GRANT, "grant-1", datetime(2026, 1, 1)
            )
        },
    ],
    ids=["named-patient", "empty-scope", "blank-purpose", "bad-actor", "naive-expiry"],
)
def test_rejects_an_invalid_query(changes):
    with pytest.raises(InvalidHistoryQuery):
        query(**changes)
