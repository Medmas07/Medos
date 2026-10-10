import json
import threading
from dataclasses import replace
from datetime import timedelta

import pytest

from adapters.outbound.fixture_patient_grants import FixturePatientGrantDirectory
from adapters.outbound.in_memory_hospital_applications import SeedError
from adapters.outbound.in_memory_synchronization import InMemorySynchronizationStore
from domain.hospital_approval import Outcome
from domain.synchronization import (
    ConsentBasis,
    NotPending,
    ScopeItem,
    SyncDecisionDraft,
    decide,
)
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_synchronization import CONTEXT, OLFA

GOVERNANCE = DEMO_DATA / "governance.json"


def store() -> InMemorySynchronizationStore:
    return InMemorySynchronizationStore.load(GOVERNANCE)


def test_seeds_the_fictional_requests_and_their_decisions():
    s = store()

    assert sorted(r.request_ref for r in s.requests()) == [
        "sync-001",
        "sync-002",
        "sync-003",
    ]
    sync_001 = s.request("sync-001")
    assert sync_001.scope == {ScopeItem.MEDICATIONS, ScopeItem.LAB_REPORTS}
    assert sync_001.consent.basis is ConsentBasis.PATIENT_GRANT
    assert sync_001.submitted_by_ref is None
    dec_002 = s.decision("dec-sync-002")
    assert (dec_002.approved_days, dec_002.outcome) == (90, Outcome.APPROVED)
    assert s.decision("dec-sync-003").valid_until is None
    # Hospital approvals are not synchronization decisions.
    assert s.decision("dec-hospital-a") is None


def test_submissions_get_the_next_number():
    s = store()
    sync_001 = s.request("sync-001")

    submitted = s.submit(
        lambda ref: replace(sync_001, request_ref=ref, submitted_at=DEMO_NOW)
    )

    assert submitted.request_ref == "sync-004"
    assert s.request("sync-004") == submitted


def test_concurrent_decisions_record_only_one():
    s = store()
    sync_001 = s.request("sync-001")
    drafts = [
        SyncDecisionDraft(
            Outcome.APPROVED, "Approbation concurrente de test.", (), 13, False
        ),
        SyncDecisionDraft(
            Outcome.REJECTED, "Rejet concurrent de test ici.", (), None, False
        ),
    ]
    recorded = []

    def attempt(draft):
        decision, decided = decide(sync_001, None, OLFA, draft, CONTEXT)
        try:
            s.record(decided, decision)
            recorded.append(decision)
        except NotPending:
            pass

    threads = [threading.Thread(target=attempt, args=(d,)) for d in drafts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(recorded) == 1
    assert s.decision("dec-sync-001") == recorded[0]


def write(tmp_path, data):
    path = tmp_path / "governance.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def seed() -> dict:
    return json.loads(GOVERNANCE.read_text(encoding="utf-8"))


def test_refuses_a_file_not_marked_fictional(tmp_path):
    data = seed()
    data["fictional"] = False

    with pytest.raises(SeedError, match="fictional"):
        InMemorySynchronizationStore.load(write(tmp_path, data))


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["synchronizationRequests"][2].update(status="approved"),
        lambda d: d["synchronizationRequests"][0].update(decisionId="dec-sync-002"),
        lambda d: d["synchronizationRequests"][0].update(scope=["xrays"]),
    ],
)
def test_refuses_inconsistent_seeds(tmp_path, change):
    data = seed()
    change(data)

    with pytest.raises(SeedError):
        InMemorySynchronizationStore.load(write(tmp_path, data))


def test_grant_directory_reads_the_fictional_grants():
    grants = FixturePatientGrantDirectory.load(DEMO_DATA / "access.json")

    def grant(patient_ref, grant_ref):
        # MOCKED: the holder is ignored; the seed grants stand for every node's.
        return grants.grant("org-hospital-b", patient_ref, grant_ref)

    grant_a = grant("pat-a", "grant-a-drx")
    assert grant_a.scope == set(ScopeItem)
    assert grant_a.active_at(DEMO_NOW)
    assert not grant_a.active_at(DEMO_NOW + timedelta(days=14))
    assert grant("pat-c", "grant-c-ines").revoked
    assert not grant("pat-a", "grant-a-ines").active_at(DEMO_NOW)
    assert grant("pat-a", "grant-unknown") is None
    # As a Hospital Node lists by patient, another patient's grant is not found.
    assert grant("pat-b", "grant-a-drx") is None
    assert (grants.mode, grants.mocked) == ("fixture", True)
