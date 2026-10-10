import json
from pathlib import Path

import pytest

from adapters.dmi.mock_local_dmi import SYSTEM_NAME, MockLocalDmi
from application.dmi_source import DmiUnavailable
from domain.dmi import PatientIdentity, RecordType, RejectedEntry, RejectionReason
from infrastructure.config import load_config
from tests.conftest import CONFIG_DIR, DEMO_NOW
from tests.dmi_port_contract import check_dmi_source

DEMO_DATA = Path(__file__).resolve().parents[3] / "demo-data"
PEOPLE = DEMO_DATA / "people.json"
UNKNOWN = PatientIdentity("pat-z", "BEN-0000-00000")
# Patient A's local identifier at each demo node (demo-data/people.json).
PATIENT_A = {
    "hospital-a": "BEN-2024-08812",
    "hospital-b": "OZ-55031",
    "private-practice": "CAB-0193",
}


def dmi_for(hospital: str, records: Path | None = None, people: Path = PEOPLE):
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")
    return MockLocalDmi(
        records or config.mock_clinical_records,
        people,
        config.identity.organization_ref,
        clock=lambda: DEMO_NOW,
    )


def refs(extract) -> set[str]:
    records = extract.records
    return {
        r.record_ref
        for r in (*records.encounters, *records.medications, *records.lab_reports)
    }


def copy_records(tmp_path: Path, hospital: str, edit=None) -> Path:
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")
    document = json.loads(config.mock_clinical_records.read_text(encoding="utf-8"))
    if edit:
        edit(document)
    path = tmp_path / f"{hospital}.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


@pytest.mark.parametrize("hospital", sorted(PATIENT_A))
def test_each_demo_dmi_passes_the_port_contract(hospital):
    known = PatientIdentity("pat-a", PATIENT_A[hospital])

    extract = check_dmi_source(dmi_for(hospital), known, UNKNOWN)

    assert extract.rejected == ()
    assert extract.extracted_at == DEMO_NOW


def test_it_describes_a_simulated_dmi_supplying_every_record_type():
    descriptor = dmi_for("hospital-a").describe()

    assert descriptor.mocked is True
    assert descriptor.system_name == SYSTEM_NAME
    assert descriptor.record_types == frozenset(RecordType)


def test_patients_are_found_by_this_hospitals_local_identifier():
    hospital_b = dmi_for("hospital-b")

    extract = hospital_b.extract_patient(PatientIdentity("pat-a", "OZ-55031"))

    assert refs(extract) == {
        "enc-b-2026-leila",
        "med-b-leila-coagulix",
        "lab-b-2026-leila",
    }
    # Another hospital's identifier for the same patient means nothing here.
    other = hospital_b.extract_patient(PatientIdentity("pat-a", "BEN-2024-08812"))
    assert refs(other) == set()


def test_records_carry_the_reference_the_node_asked_for():
    extract = dmi_for("hospital-a").extract_patient(
        PatientIdentity("pat-q7", "BEN-2024-08812")
    )

    assert refs(extract) == {"enc-a-2024-leila-er", "lab-a-2024-leila"}
    assert {
        r.patient_ref
        for r in (*extract.records.encounters, *extract.records.lab_reports)
    } == {"pat-q7"}


@pytest.mark.parametrize("hospital", sorted(PATIENT_A))
def test_every_patient_with_records_here_is_reachable_through_the_dmi(hospital):
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")
    document = json.loads(config.mock_clinical_records.read_text(encoding="utf-8"))
    people = json.loads(PEOPLE.read_text(encoding="utf-8"))["patients"]
    dmi = dmi_for(hospital)

    extracted = set()
    for person in people:
        for local in person["localIdentifiers"]:
            if local["organizationId"] == config.identity.organization_ref:
                identity = PatientIdentity(person["id"], local["value"])
                extracted |= refs(dmi.extract_patient(identity))

    held = {
        e["id"]
        for collection in ("encounters", "medications", "labReports")
        for e in document[collection]
    }
    assert extracted == held


def test_unreadable_entries_are_rejected_and_the_rest_returned(tmp_path):
    def break_entries(document):
        del document["encounters"][0]["startedAt"]
        document["labReports"][0]["results"][0]["flag"] = "critical"
        document["labReports"][0]["id"] = ""

    records = copy_records(tmp_path, "hospital-a", break_entries)

    extract = dmi_for("hospital-a", records).extract_patient(
        PatientIdentity("pat-a", "BEN-2024-08812")
    )

    assert refs(extract) == set()
    assert extract.rejected == (
        RejectedEntry(
            "enc-a-2024-leila-er",
            RecordType.ENCOUNTERS,
            RejectionReason.MISSING_FIELD,
        ),
        RejectedEntry(
            "labReports[0]", RecordType.LAB_REPORTS, RejectionReason.INVALID_VALUE
        ),
    )
    # Another patient's records are untouched by those entries.
    karim = dmi_for("hospital-a", records).extract_patient(
        PatientIdentity("pat-b", "BEN-2025-11407")
    )
    assert len(refs(karim)) == 4
    assert karim.rejected == ()


def test_it_reads_the_dmi_on_every_extraction(tmp_path):
    records = copy_records(tmp_path, "hospital-a")
    dmi = dmi_for("hospital-a", records)
    patient = PatientIdentity("pat-a", "BEN-2024-08812")
    before = dmi.extract_patient(patient)

    document = json.loads(records.read_text(encoding="utf-8"))
    document["labReports"] = [
        r for r in document["labReports"] if r["id"] != "lab-a-2024-leila"
    ]
    records.write_text(json.dumps(document), encoding="utf-8")

    assert refs(before) - refs(dmi.extract_patient(patient)) == {"lab-a-2024-leila"}


def test_a_missing_dmi_does_not_stop_construction_but_cannot_answer(tmp_path):
    dmi = dmi_for("hospital-a", tmp_path / "absent.json")

    assert dmi.describe().mocked is True
    with pytest.raises(DmiUnavailable):
        dmi.extract_patient(UNKNOWN)


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d.update(fictional=False),
        lambda d: d.update(heldBy="org-hospital-b"),
        lambda d: d.update(medications=None),
        lambda d: d["encounters"].append("not an entry"),
    ],
)
def test_a_source_it_cannot_trust_or_read_is_unavailable(tmp_path, edit):
    records = copy_records(tmp_path, "hospital-a", edit)

    with pytest.raises(DmiUnavailable):
        dmi_for("hospital-a", records).extract_patient(UNKNOWN)


def test_another_hospitals_records_file_is_refused():
    hospital_b_records = load_config(
        CONFIG_DIR / "hospital-b.demo.json"
    ).mock_clinical_records

    with pytest.raises(DmiUnavailable, match="held by"):
        dmi_for("hospital-a", hospital_b_records).extract_patient(UNKNOWN)


@pytest.mark.parametrize("content", ["{", '{"fictional": true}', "[]"])
def test_an_unreadable_patient_index_is_unavailable(tmp_path, content):
    people = tmp_path / "people.json"
    people.write_text(content, encoding="utf-8")

    with pytest.raises(DmiUnavailable):
        dmi_for("hospital-a", people=people).extract_patient(UNKNOWN)
