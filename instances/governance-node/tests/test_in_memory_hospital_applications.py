import json
import threading

import pytest

from adapters.outbound.fixture_reviewer_directory import FixtureReviewerDirectory
from adapters.outbound.in_memory_hospital_applications import (
    InMemoryHospitalApplicationStore,
    SeedError,
)
from domain.hospital_application import ApplicationStatus
from domain.hospital_approval import (
    DecisionDraft,
    NotAwaitingReview,
    Outcome,
    decide,
)
from tests.test_policy import DEMO_POLICY
from tests.conftest import DEMO_DATA, DEMO_NOW

GOVERNANCE = DEMO_DATA / "governance.json"


def store() -> InMemoryHospitalApplicationStore:
    return InMemoryHospitalApplicationStore.load(GOVERNANCE)


def test_seeds_the_fictional_applications_and_their_decisions():
    s = store()

    assert {a.application_ref: a.status.value for a in s.applications()} == {
        "app-hospital-a": "approved",
        "app-hospital-b": "approved",
        "app-private-practice": "approved",
        "app-hospital-c": "human_review",
    }
    assert s.decision("dec-hospital-b").organization_ref == "org-hospital-b"
    # Decisions on other subjects are not hospital approvals.
    assert s.decision("dec-sync-002") is None


def test_maps_hospital_c_findings_from_its_documents_and_review_steps():
    findings = store().application("app-hospital-c").findings

    assert [d.document_ref for d in findings.missing_documents] == ["doc-c-assurance"]
    assert findings.unaccepted_agreements == ()
    assert findings.completeness_findings == ("Attestation d'assurance manquante.",)
    assert len(findings.advisory_findings) == 2
    assert findings.count == 4


def test_record_refuses_an_application_decided_in_the_meantime():
    s = store()
    hospital_c = s.application("app-hospital-c")
    first = decide(
        hospital_c,
        FixtureReviewerDirectory.load(DEMO_DATA / "people.json").reviewer("usr-olfa"),
        DecisionDraft(Outcome.REJECTED, "Dossier insuffisant à ce stade.", (), True),
        DEMO_POLICY,
        DEMO_NOW,
    )
    s.record(*reversed(first))

    with pytest.raises(NotAwaitingReview):
        s.record(*reversed(first))
    assert s.application("app-hospital-c").status is ApplicationStatus.REJECTED


def test_concurrent_decisions_record_only_one():
    s = store()
    hospital_c = s.application("app-hospital-c")
    olfa = FixtureReviewerDirectory.load(DEMO_DATA / "people.json").reviewer("usr-olfa")
    drafts = [
        DecisionDraft(Outcome.APPROVED, "Approbation concurrente.", ("C",), True),
        DecisionDraft(Outcome.REJECTED, "Rejet concurrent de test.", (), True),
    ]
    recorded = []

    def attempt(draft: DecisionDraft) -> None:
        decision, decided = decide(hospital_c, olfa, draft, DEMO_POLICY, DEMO_NOW)
        try:
            s.record(decided, decision)
            recorded.append(decision)
        except NotAwaitingReview:
            pass

    threads = [threading.Thread(target=attempt, args=(d,)) for d in drafts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(recorded) == 1
    assert s.decision("dec-hospital-c") == recorded[0]


def write(tmp_path, data) -> object:
    path = tmp_path / "governance.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def seed() -> dict:
    return json.loads(GOVERNANCE.read_text(encoding="utf-8"))


def test_refuses_a_file_not_marked_fictional(tmp_path):
    data = seed()
    data["fictional"] = False

    with pytest.raises(SeedError, match="fictional"):
        InMemoryHospitalApplicationStore.load(write(tmp_path, data))


def test_refuses_an_application_citing_a_decision_that_is_not_its_own(tmp_path):
    data = seed()
    app_a = next(a for a in data["hospitalApplications"] if a["id"] == "app-hospital-a")
    app_a["decisionId"] = "dec-hospital-b"

    with pytest.raises(SeedError):
        InMemoryHospitalApplicationStore.load(write(tmp_path, data))


def test_refuses_a_malformed_file(tmp_path):
    with pytest.raises(SeedError):
        InMemoryHospitalApplicationStore.load(write(tmp_path, {"fictional": True}))
    with pytest.raises(SeedError):
        InMemoryHospitalApplicationStore.load(tmp_path / "missing.json")


def test_reviewer_directory_knows_staff_and_clinicians_but_not_patients():
    directory = FixtureReviewerDirectory.load(DEMO_DATA / "people.json")

    assert directory.reviewer("usr-olfa").role == "governance_reviewer"
    assert directory.reviewer("usr-mehdi").organization_ref == "org-hospital-c"
    assert directory.reviewer("clin-x").role == "physician"
    assert directory.reviewer("pat-a") is None
