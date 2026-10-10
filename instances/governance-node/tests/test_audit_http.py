"""The governance audit API against contracts/api/governance/governance-audit-events.v1.yaml.

Every response is checked against the contract schema for its status, and the
contract's examples are the expected answers on the demo data. The other governance
APIs record their events here: a submission, a decision, and every check answered.
"""

import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_DATA
from tests.test_research_http import APPROVE_002, JOB_001, NEW
from tests.test_synchronization_http import (
    APPROVE_001,
    ASK_A,
    NEW_B,
    Clock,
    check,
    example,
    load,
)

AUDIT = load("api/governance/governance-audit-events.v1.yaml")
LIST = AUDIT["paths"]["/v1/audit/events"]["get"]
DETAIL = AUDIT["paths"]["/v1/audit/events/{event_ref}"]["get"]


@pytest.fixture
def client() -> TestClient:
    # A fresh app per test: each keeps its own trail in memory.
    return TestClient(create_app(demo_data=DEMO_DATA, clock=Clock()))


def events(client, query: str = "") -> list[dict]:
    return check(client.get(f"/v1/audit/events{query}"), AUDIT, LIST, 200)["events"]


def test_lists_the_seed_events_newest_first(client):
    body = check(client.get("/v1/audit/events"), AUDIT, LIST, 200)

    assert body["durable"] is False
    assert [e["event_ref"] for e in body["events"]] == [
        f"evt-{n:03d}" for n in range(7, 0, -1)
    ]
    assert check(
        client.get("/v1/audit/events?organization_ref=org-hospital-b"), AUDIT, LIST, 200
    ) == example(AUDIT, LIST, 200, "hospitalB")


def test_filters_combine_and_limit(client):
    assert [e["event_ref"] for e in events(client, "?domain=hospital_approval")] == [
        "evt-006",
        "evt-002",
        "evt-001",
    ]
    assert [
        e["event_ref"]
        for e in events(client, "?domain=synchronization&action=decision_recorded")
    ] == ["evt-005", "evt-003"]
    assert [e["event_ref"] for e in events(client, "?limit=2")] == [
        "evt-007",
        "evt-006",
    ]
    assert check(
        client.get("/v1/audit/events?subject_ref=dec-unknown"), AUDIT, LIST, 200
    ) == example(AUDIT, LIST, 200, "empty")


@pytest.mark.parametrize(
    "query, field",
    [
        ("?limit=0", "limit"),
        ("?limit=501", "limit"),
        ("?limit=x", "limit"),
        ("?domain=billing", "domain"),
        ("?action=deleted", "action"),
        ("?organization_ref=org%20b", "organization_ref"),
        ("?patient_ref=pat-a", "patient_ref"),
        ("?limit=1&limit=2", "limit"),
    ],
)
def test_rejects_invalid_unknown_or_repeated_filters(client, query, field):
    body = check(client.get(f"/v1/audit/events{query}"), AUDIT, LIST, 400)

    assert body["code"] == "invalid_request"
    assert body["detail"] == f"Invalid or unknown parameters: {field}"


def test_reads_one_event(client):
    assert check(client.get("/v1/audit/events/evt-004"), AUDIT, DETAIL, 200) == example(
        AUDIT, DETAIL, 200, "evt004"
    )
    assert check(client.get("/v1/audit/events/evt-999"), AUDIT, DETAIL, 404) == example(
        AUDIT, DETAIL, 404, "unknown"
    )


def test_a_synchronization_flow_is_audited_without_patient_data(client):
    submitted = client.post("/v1/synchronization-requests", json=NEW_B).json()
    client.post("/v1/synchronization-requests/sync-001/decision", json=APPROVE_001)
    client.post("/v1/synchronization-authorizations/dec-sync-001/checks", json=ASK_A)
    client.post(
        "/v1/synchronization-authorizations/dec-sync-001/checks",
        json={**ASK_A, "patient_ref": "pat-b"},
    )

    recorded = events(client, "?limit=4")
    assert [
        (e["action"], e["subject_ref"], e["actor_ref"], e["outcome"], e["reason"])
        for e in recorded
    ] == [
        (
            "authorization_checked",
            "dec-sync-001",
            "clin-x",
            "denied",
            "patient_mismatch",
        ),
        ("authorization_checked", "dec-sync-001", "clin-x", "authorized", None),
        ("decision_recorded", "dec-sync-001", "usr-olfa", "approved", None),
        (
            "request_received",
            submitted["request_ref"],
            NEW_B["submitted_by_ref"],
            None,
            None,
        ),
    ]
    assert recorded[1]["organization_refs"] == [
        "org-governance",
        "org-hospital-a",
        "org-hospital-b",
    ]
    # Minimized: no patient reference, purpose, or scope.
    text = str(recorded)
    for value in ("pat-a", "pat-b", ASK_A["purpose"], "medications"):
        assert value not in text


def test_the_expired_check_example_is_what_the_node_records(client):
    client.post(
        "/v1/synchronization-authorizations/dec-sync-002/checks",
        json={**ASK_A, "requester_organization_ref": "org-private-practice"},
    )

    assert check(
        client.get(
            "/v1/audit/events?subject_ref=dec-sync-002&action=authorization_checked"
        ),
        AUDIT,
        LIST,
        200,
    ) == example(AUDIT, LIST, 200, "deniedCheck")


def test_a_research_flow_is_audited_and_refusals_are_not(client):
    client.post("/v1/research-requests", json=NEW)
    client.post(
        "/v1/research-requests/rar-002/decision",
        json={**APPROVE_002, "reviewer_ref": "usr-aymen"},
    )  # 403: not audited
    client.post("/v1/research-requests/rar-002/decision", json=APPROVE_002)
    client.post("/v1/research-authorizations/check", json=JOB_001)
    client.post(
        "/v1/research-authorizations/check",
        json={**JOB_001, "decision_ref": "dec-rar-404"},
    )  # 404: not audited

    recorded = events(client, "?domain=research&limit=3")
    assert [(e["action"], e["subject_ref"], e["outcome"]) for e in recorded] == [
        ("authorization_checked", "dec-rar-001", "authorized"),
        ("decision_recorded", "dec-rar-002", "approved"),
        ("request_received", "rar-003", None),
    ]
    assert recorded[0]["actor_ref"] == JOB_001["requested_by"]
    assert len(events(client)) == 10


def test_a_hospital_approval_is_audited(client):
    client.post(
        "/v1/hospital-applications/app-hospital-c/decision",
        json={
            "reviewer_ref": "usr-olfa",
            "outcome": "approved",
            "rationale": "Dossier conforme, sous réserve de l’attestation d’assurance.",
            "conditions": ["Transmettre l’attestation d’assurance sous 30 jours."],
            "findings_acknowledged": True,
        },
    )

    [event] = events(client, "?organization_ref=org-hospital-c&limit=1")
    assert (event["event_ref"], event["subject_ref"], event["outcome"]) == (
        "evt-008",
        "dec-hospital-c",
        "approved",
    )
    assert event["organization_refs"] == ["org-governance", "org-hospital-c"]


def test_runtime_events_are_lost_on_restart(client):
    client.post("/v1/synchronization-authorizations/dec-sync-001/checks", json=ASK_A)
    assert len(events(client)) == 8

    restarted = TestClient(create_app(demo_data=DEMO_DATA, clock=Clock()))
    assert len(events(restarted)) == 7
