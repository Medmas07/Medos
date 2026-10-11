import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from adapters.dmi.zitoun_sih_export import (
    SYSTEM_NAME,
    DmiConfigError,
    ZitounSihExportDmi,
)
from adapters.outbound.fixture_clinical_repository import FixtureClinicalRepository
from application.dmi_source import DmiUnavailable
from domain.clinical_record import LabFlag
from domain.dmi import PatientIdentity, RecordType, RejectedEntry, RejectionReason
from infrastructure.config import load_config
from tests.conftest import CONFIG_DIR
from tests.dmi_port_contract import check_dmi_source

DMI_CONFIG = CONFIG_DIR / "hospital-b.dmi.json"
PATIENT_A = PatientIdentity("pat-a", "OZ-55031")
PATIENT_C = PatientIdentity("pat-c", "OZ-61822")
UNKNOWN = PatientIdentity("pat-z", "OZ-00000")


def export_document() -> dict:
    config = json.loads(DMI_CONFIG.read_text(encoding="utf-8"))
    path = (DMI_CONFIG.parent / config["export_file"]).resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def dmi_with(tmp_path: Path, edit=None, config_edit=None) -> ZitounSihExportDmi:
    """The adapter over an edited copy of the export and of its configuration."""
    document = export_document()
    if edit:
        edit(document)
    (tmp_path / "export.json").write_text(json.dumps(document), encoding="utf-8")
    config = json.loads(DMI_CONFIG.read_text(encoding="utf-8"))
    config["export_file"] = "export.json"
    if config_edit:
        config_edit(config)
    path = tmp_path / "dmi.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return ZitounSihExportDmi.from_config(path)


def refs(extract) -> set[str]:
    records = extract.records
    return {
        r.record_ref
        for r in (*records.encounters, *records.medications, *records.lab_reports)
    }


def without_refs(records):
    """Records with the references blanked: the DMI's ids are not the fixture's."""
    return [
        replace(
            r,
            record_ref="ref",
            **({"encounter_ref": None} if hasattr(r, "encounter_ref") else {}),
        )
        for r in records
    ]


@pytest.mark.parametrize("known", [PATIENT_A, PATIENT_C])
def test_it_passes_the_port_contract(known):
    extract = check_dmi_source(
        ZitounSihExportDmi.from_config(DMI_CONFIG), known, UNKNOWN
    )

    assert extract.rejected == ()


def test_it_describes_hospital_bs_simulated_dmi():
    descriptor = ZitounSihExportDmi.from_config(DMI_CONFIG).describe()

    assert descriptor.system_name == SYSTEM_NAME
    assert descriptor.record_types == frozenset(RecordType)
    assert descriptor.mocked is True


@pytest.mark.parametrize("patient", [PATIENT_A, PATIENT_C])
def test_the_legacy_export_maps_to_hospital_bs_canonical_records(patient):
    """The export and records/hospital-b.json describe the same fictional records; the
    mapping must reproduce every clinical field, from local codes and formats."""
    config = load_config(CONFIG_DIR / "hospital-b.demo.json")
    expected = FixtureClinicalRepository.load(
        config.mock_clinical_records, config.identity.organization_ref
    ).patient_records(patient.patient_ref)

    extracted = (
        ZitounSihExportDmi.from_config(DMI_CONFIG).extract_patient(patient).records
    )

    for kind in ("encounters", "medications", "lab_reports"):
        assert without_refs(getattr(extracted, kind)) == without_refs(
            getattr(expected, kind)
        )


def test_references_are_prefixed_dmi_ids_and_links_resolve():
    extract = ZitounSihExportDmi.from_config(DMI_CONFIG).extract_patient(PATIENT_A)

    assert refs(extract) == {"dmi-b-S2026-1142", "dmi-b-40217", "dmi-b-B2026-0751"}
    linked = {
        r.encounter_ref
        for r in (*extract.records.medications, *extract.records.lab_reports)
    }
    assert linked == {e.record_ref for e in extract.records.encounters}


def test_patients_are_found_by_hospital_bs_ipp_only():
    dmi = ZitounSihExportDmi.from_config(DMI_CONFIG)

    # Patient A's identifier at Hospital A means nothing to Hospital B's DMI.
    assert (
        refs(dmi.extract_patient(PatientIdentity("pat-a", "BEN-2024-08812"))) == set()
    )
    # Records carry the reference the Node asked for, not the IPP.
    extract = dmi.extract_patient(PatientIdentity("pat-q7", "OZ-55031"))
    assert {r.patient_ref for r in extract.records.encounters} == {"pat-q7"}


def test_extracted_at_is_when_the_dmi_wrote_the_export():
    extract = ZitounSihExportDmi.from_config(DMI_CONFIG).extract_patient(PATIENT_A)

    assert extract.extracted_at == datetime.fromisoformat("2026-10-10T02:00:00+01:00")


def test_flags_are_the_dmis_and_never_recomputed_from_the_range(tmp_path):
    def flag_high(document):
        document["resultats_bio"][0]["indicateur"] = "H"

    extract = dmi_with(tmp_path, flag_high).extract_patient(PATIENT_A)

    result = extract.records.lab_reports[0].results[0]
    assert (result.value, result.flag) == (12.6, LabFlag.HIGH)


def _edit(collection: str, index: int, **changes):
    def edit(document):
        row = document[collection][index]
        for key, value in changes.items():
            if value is ...:
                del row[key]
            else:
                row[key] = value

    return edit


@pytest.mark.parametrize(
    ("edit", "rejected"),
    [
        (
            _edit("prescriptions", 0, code_produit="COAG10"),
            RejectedEntry(
                "40217", RecordType.MEDICATIONS, RejectionReason.UNMAPPED_CODE
            ),
        ),
        # Codes match exactly as the DMI writes them; nothing is case-folded.
        (
            _edit("prescriptions", 0, etat="en cours"),
            RejectedEntry(
                "40217", RecordType.MEDICATIONS, RejectionReason.UNMAPPED_CODE
            ),
        ),
        # An unknown prescriber rejects the prescription rather than dropping the prescriber.
        (
            _edit("prescriptions", 0, prescripteur="MAT-9999"),
            RejectedEntry(
                "40217", RecordType.MEDICATIONS, RejectionReason.UNMAPPED_CODE
            ),
        ),
        (
            _edit("prescriptions", 0, date_debut="2026-05-20"),
            RejectedEntry(
                "40217", RecordType.MEDICATIONS, RejectionReason.INVALID_VALUE
            ),
        ),
        (
            _edit("sejours", 1, type_venue="HOSP"),
            RejectedEntry(
                "S2026-1142", RecordType.ENCOUNTERS, RejectionReason.UNMAPPED_CODE
            ),
        ),
        (
            _edit("sejours", 1, num_sejour=...),
            RejectedEntry(
                "sejours[1]", RecordType.ENCOUNTERS, RejectionReason.MISSING_FIELD
            ),
        ),
        (
            _edit("sejours", 1, libelle=" "),
            RejectedEntry(
                "S2026-1142", RecordType.ENCOUNTERS, RejectionReason.INVALID_VALUE
            ),
        ),
        # The DMI writes a decimal comma; anything else is not its number.
        (
            _edit("resultats_bio", 0, valeur="12.6"),
            RejectedEntry(
                "B2026-0751", RecordType.LAB_REPORTS, RejectionReason.INVALID_VALUE
            ),
        ),
        (
            _edit("resultats_bio", 1, indicateur="HH"),
            RejectedEntry(
                "B2026-0751", RecordType.LAB_REPORTS, RejectionReason.UNMAPPED_CODE
            ),
        ),
        (
            _edit("resultats_bio", 2, borne_sup=""),
            RejectedEntry(
                "B2026-0751", RecordType.LAB_REPORTS, RejectionReason.INVALID_VALUE
            ),
        ),
        # Rows of one report must agree on the report's own fields.
        (
            _edit("resultats_bio", 2, date_prelevement="21/05/2026 08:00"),
            RejectedEntry(
                "B2026-0751", RecordType.LAB_REPORTS, RejectionReason.INVALID_VALUE
            ),
        ),
    ],
)
def test_an_entry_that_cannot_map_is_rejected_whole_and_the_rest_returned(
    tmp_path, edit, rejected
):
    extract = dmi_with(tmp_path, edit).extract_patient(PATIENT_A)

    assert extract.rejected == (rejected,)
    # Only the rejected entry is missing; one bad lab row rejects its whole report.
    assert len(refs(extract)) == 2


def test_a_lab_row_without_a_request_number_is_rejected_by_position(tmp_path):
    extract = dmi_with(
        tmp_path, _edit("resultats_bio", 1, num_demande=...)
    ).extract_patient(PATIENT_A)

    assert extract.rejected == (
        RejectedEntry(
            "resultats_bio[1]", RecordType.LAB_REPORTS, RejectionReason.MISSING_FIELD
        ),
    )
    # The request's other rows still form a report.
    assert len(extract.records.lab_reports[0].results) == 2


def test_another_patients_rows_are_untouched_by_a_rejection(tmp_path):
    dmi = dmi_with(tmp_path, _edit("sejours", 1, type_venue="HOSP"))

    nour = dmi.extract_patient(PATIENT_C)

    assert refs(nour) == {"dmi-b-S2025-3381"}
    assert nour.rejected == ()


def test_it_reads_the_export_on_every_extraction(tmp_path):
    dmi = dmi_with(tmp_path)
    before = dmi.extract_patient(PATIENT_A)

    path = tmp_path / "export.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["prescriptions"] = []
    path.write_text(json.dumps(document), encoding="utf-8")

    assert refs(before) - refs(dmi.extract_patient(PATIENT_A)) == {"dmi-b-40217"}


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d.update(fictional=False),
        lambda d: d.update(etablissement="BEN-TUNIS"),
        lambda d: d.update(date_export="2026-10-10T02:00:00+01:00"),
        lambda d: d.pop("date_export"),
        lambda d: d.update(prescriptions=None),
        lambda d: d["sejours"].append("not a row"),
    ],
)
def test_an_export_it_cannot_trust_or_read_is_unavailable(tmp_path, edit):
    with pytest.raises(DmiUnavailable):
        dmi_with(tmp_path, edit).extract_patient(UNKNOWN)


def test_a_missing_export_does_not_stop_construction_but_cannot_answer(tmp_path):
    dmi = dmi_with(tmp_path)
    (tmp_path / "export.json").unlink()

    assert dmi.describe().mocked is True
    with pytest.raises(DmiUnavailable):
        dmi.extract_patient(UNKNOWN)


@pytest.mark.parametrize(
    "config_edit",
    [
        # A table with any non-canonical value is refused whole (HC-122).
        lambda c: c["mapping"]["tables"]["lab_flags"].update(HH="critical"),
        lambda c: c["mapping"].pop("version"),
        lambda c: c.pop("establishment_code"),
        lambda c: c.update(host="dmi.example"),
    ],
)
def test_an_unusable_configuration_stops_the_adapter(tmp_path, config_edit):
    with pytest.raises(DmiConfigError):
        dmi_with(tmp_path, config_edit=config_edit)


def test_a_missing_configuration_stops_the_adapter(tmp_path):
    with pytest.raises(DmiConfigError):
        ZitounSihExportDmi.from_config(tmp_path / "absent.json")
