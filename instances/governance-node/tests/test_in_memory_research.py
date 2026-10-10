import json
import threading
from dataclasses import replace
from datetime import date

import pytest

from adapters.outbound.in_memory_hospital_applications import SeedError
from adapters.outbound.in_memory_research import InMemoryResearchStore
from domain.hospital_approval import Outcome
from domain.research import NotUnderReview, Population, decide
from tests.test_policy import DEMO_POLICY
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_research import APPROVE, APPROVED_ORGS, OLFA, REJECT

GOVERNANCE, RESEARCH = DEMO_DATA / "governance.json", DEMO_DATA / "research.json"


def store() -> InMemoryResearchStore:
    return InMemoryResearchStore.load(GOVERNANCE, RESEARCH)


def test_seeds_the_requests_with_their_project_content():
    s = store()

    rar_002 = s.request("rar-002")
    assert rar_002.project_ref == "proj-002"
    assert rar_002.principal_investigator_ref == "usr-aymen"
    assert rar_002.participating_organization_refs == (
        "org-hospital-b",
        "org-private-practice",
    )
    assert rar_002.data_scope.population == Population(age_min=18, age_max=30)
    assert rar_002.protocol_document_ref == "doc-proj-002-protocole"
    assert s.request("rar-001").data_scope.population == Population(
        40, 79, date(2024, 1, 1), date(2026, 12, 31)
    )


def test_seeds_the_structured_authorization_of_dec_rar_001():
    decision = store().decision("dec-rar-001")

    assert decision.outcome is Outcome.APPROVED
    assert decision.approved_organization_refs == ("org-hospital-a", "org-hospital-b")
    assert decision.approved_variables == (
        "age_band",
        "sex",
        "hba1c",
        "treated_hypertension",
    )
    assert decision.minimum_cell_size == 10
    # Other subjects' decisions are not research decisions.
    assert store().decision("dec-sync-002") is None


def test_submissions_get_the_next_number():
    s = store()
    # The builder runs while the store is locked, so it must not call the store.
    rar_002 = s.request("rar-002")

    submitted = s.submit(lambda ref: replace(rar_002, request_ref=ref))

    assert submitted.request_ref == "rar-003"


def test_concurrent_decisions_record_only_one():
    s = store()
    rar_002 = s.request("rar-002")
    approve = replace(
        APPROVE,
        approved_organization_refs=("org-hospital-b",),
        approved_variables=("age_band",),
    )
    recorded = []

    def attempt(draft):
        decision, decided = decide(
            rar_002, None, OLFA, draft, APPROVED_ORGS, DEMO_POLICY, DEMO_NOW
        )
        try:
            s.record(decided, decision)
            recorded.append(decision)
        except NotUnderReview:
            pass

    threads = [threading.Thread(target=attempt, args=(d,)) for d in (approve, REJECT)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(recorded) == 1
    assert s.decision("dec-rar-002") == recorded[0]


def write(tmp_path, governance=None, research=None):
    g, r = tmp_path / "governance.json", tmp_path / "research.json"
    g.write_text(
        json.dumps(governance or json.loads(GOVERNANCE.read_text(encoding="utf-8"))),
        encoding="utf-8",
    )
    r.write_text(
        json.dumps(research or json.loads(RESEARCH.read_text(encoding="utf-8"))),
        encoding="utf-8",
    )
    return g, r


@pytest.mark.parametrize(
    "file, change",
    [
        ("research", lambda d: d.update(fictional=False)),
        ("research", lambda d: d["projects"][0].pop("dataScope")),
        (
            "research",
            lambda d: d["projects"][0]["dataScope"].update(variables=["HbA1c %"]),
        ),
        (
            "governance",
            lambda d: d["researchAccessRequests"][1].update(status="approved"),
        ),
        (
            "governance",
            lambda d: d["researchAccessRequests"][0].update(projectId="proj-404"),
        ),
    ],
)
def test_refuses_inconsistent_seeds(tmp_path, file, change):
    data = {
        "governance": json.loads(GOVERNANCE.read_text(encoding="utf-8")),
        "research": json.loads(RESEARCH.read_text(encoding="utf-8")),
    }
    change(data[file])

    with pytest.raises(SeedError):
        InMemoryResearchStore.load(
            *write(tmp_path, data["governance"], data["research"])
        )
