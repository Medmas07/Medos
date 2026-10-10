from application.get_node_status import get_node_status
from domain.clinical_record import PatientRecords, RepositorySummary
from domain.node_identity import NodeIdentity
from domain.node_status import SKELETON_NOTICE

IDENTITY = NodeIdentity(node_ref="node-test", organization_ref="org-test")
SUMMARY = RepositorySummary(mocked=True, encounters=3, medications=1, lab_reports=2)


class StubRepository:
    def patient_records(self, patient_ref: str) -> PatientRecords:
        return PatientRecords()

    def summary(self) -> RepositorySummary:
        return SUMMARY


def status():
    return get_node_status(IDENTITY, StubRepository())


def test_reports_the_configured_hospital_identity():
    assert (status().node_ref, status().organization_ref) == ("node-test", "org-test")


def test_reports_the_patient_history_capability():
    assert status().capabilities == ("patient_history",)


def test_reports_the_clinical_repository_summary():
    assert status().clinical_records == SUMMARY


def test_states_the_skeleton_boundary():
    assert status().notice == SKELETON_NOTICE
