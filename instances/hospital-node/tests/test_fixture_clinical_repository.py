import json
from pathlib import Path

import pytest

from adapters.outbound.fixture_clinical_repository import (
    ClinicalFixtureError,
    FixtureClinicalRepository,
)
from domain.clinical_record import LabFlag, MedicationStatus, PatientRecords
from infrastructure.config import load_config
from tests.conftest import CONFIG_DIR, DEMO_CONFIGS

RECORDS_DIR = Path(__file__).resolve().parents[3] / "demo-data" / "records"


def repository_for(hospital: str) -> FixtureClinicalRepository:
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")
    return FixtureClinicalRepository.load(
        config.mock_clinical_records, config.identity.organization_ref
    )


def refs(records: PatientRecords) -> set[str]:
    return {
        r.record_ref
        for r in records.encounters + records.medications + records.lab_reports
    }


@pytest.mark.parametrize("path", DEMO_CONFIGS, ids=lambda p: p.stem)
def test_each_demo_node_loads_every_record_its_organization_holds(path):
    config = load_config(path)
    fixture = json.loads(config.mock_clinical_records.read_text(encoding="utf-8"))
    repository = FixtureClinicalRepository.load(
        config.mock_clinical_records, config.identity.organization_ref
    )

    summary = repository.summary()
    assert summary.mocked is True
    assert (summary.encounters, summary.medications, summary.lab_reports) == (
        len(fixture["encounters"]),
        len(fixture["medications"]),
        len(fixture["labReports"]),
    )


def test_returns_only_the_requested_patients_records():
    records = repository_for("hospital-a").patient_records("pat-a")

    assert refs(records) == {"enc-a-2024-leila-er", "lab-a-2024-leila"}
    assert records.medications == ()


def test_maps_fixture_fields_to_the_domain_model():
    records = repository_for("hospital-b").patient_records("pat-a")

    (medication,) = records.medications
    assert medication.code == "MED-COAGULIX"
    assert medication.status is MedicationStatus.ACTIVE
    assert medication.end_date is None
    assert medication.encounter_ref == "enc-b-2026-leila"

    (report,) = records.lab_reports
    assert report.collected_at.utcoffset() is not None
    assert {r.flag for r in report.results} == {LabFlag.NORMAL}
    assert report.results[0].reference_range.low == 12.0


def test_never_holds_another_hospitals_records():
    # Patient A also has records at Hospital B and the private practice.
    assert all(
        r.startswith(("enc-a-", "med-a-", "lab-a-"))
        for r in refs(repository_for("hospital-a").patient_records("pat-a"))
    )


@pytest.mark.parametrize("patient_ref", ["pat-c", "pat-unknown"])
def test_unknown_and_absent_patients_get_the_same_empty_answer(patient_ref):
    # Patient C has records at Hospital B and the private practice, none here.
    assert repository_for("hospital-a").patient_records(patient_ref) == (
        PatientRecords()
    )


def test_refuses_a_file_held_by_another_organization():
    with pytest.raises(ClinicalFixtureError, match="held by 'org-hospital-b'"):
        FixtureClinicalRepository.load(
            RECORDS_DIR / "hospital-b.json", "org-hospital-a"
        )


def write_fixture(tmp_path: Path, content) -> Path:
    path = tmp_path / "records.json"
    path.write_text(content if isinstance(content, str) else json.dumps(content))
    return path


VALID = {
    "fictional": True,
    "heldBy": "org-test",
    "encounters": [],
    "medications": [],
    "labReports": [],
}
BAD_MEDICATION = {
    "id": "med-test",
    "patientId": "pat-test",
    "medicationCode": "MED-TEST",
    "startDate": "2026-01-01",
    "status": "paused",
}
NAIVE_ENCOUNTER = {
    "id": "enc-test",
    "patientId": "pat-test",
    "type": "consultation",
    "title": "Consultation",
    "startedAt": "2026-01-01T09:00:00",
    "clinicianId": "clin-test",
}


def test_loads_an_empty_fixture(tmp_path):
    repository = FixtureClinicalRepository.load(
        write_fixture(tmp_path, VALID), "org-test"
    )

    assert repository.patient_records("pat-test") == PatientRecords()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not json", "Cannot read"),
        ({**VALID, "fictional": False}, "not marked fictional"),
        ({k: v for k, v in VALID.items() if k != "fictional"}, "not marked fictional"),
        ({k: v for k, v in VALID.items() if k != "labReports"}, "Invalid"),
        ({**VALID, "medications": [BAD_MEDICATION]}, "Invalid"),
        ({**VALID, "encounters": [NAIVE_ENCOUNTER]}, "Invalid"),
    ],
    ids=[
        "malformed",
        "not-fictional",
        "no-fictional-marker",
        "missing-list",
        "unknown-status",
        "time-without-offset",
    ],
)
def test_refuses_an_invalid_fixture(tmp_path, content, message):
    with pytest.raises(ClinicalFixtureError, match=message):
        FixtureClinicalRepository.load(write_fixture(tmp_path, content), "org-test")


def test_refuses_a_missing_file(tmp_path):
    with pytest.raises(ClinicalFixtureError, match="Cannot read"):
        FixtureClinicalRepository.load(tmp_path / "absent.json", "org-test")
