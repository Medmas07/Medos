import copy
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from infrastructure.config import load_config
from main import create_app
from tests.conftest import CONFIG_DIR, DEMO_NOW

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
AUDIT = yaml.safe_load(
    (CONTRACTS / "api" / "hospital-audit" / "hospital-audit-events.v1.yaml").read_text(
        encoding="utf-8"
    )
)
FEDERATION = yaml.safe_load(
    (CONTRACTS / "federation" / "hospital-node-federation.v1.yaml").read_text(
        encoding="utf-8"
    )
)
DR_X_MEDICATIONS = FEDERATION["paths"]["/v1/federation/queries"]["post"]["requestBody"][
    "content"
]["application/json"]["examples"]["drXPatientA"]["value"]
OTHER_QUERY_ID = "1c2d3e4f-5a6b-4c7d-8e9f-0a1b2c3d4e5f"


def schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": AUDIT["components"]},
        format_checker=FormatChecker(),
    )


def client_for(hospital: str) -> TestClient:
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")
    return TestClient(create_app(config, clock=lambda: DEMO_NOW))


def ask(client: TestClient, **changes):
    body = copy.deepcopy(DR_X_MEDICATIONS) | changes
    return client.post("/v1/federation/queries", json=body)


def trail(client: TestClient, **params) -> dict:
    response = client.get("/v1/audit/events", params=params)
    assert response.status_code == 200
    schema("AuditEventList").validate(response.json())
    return response.json()


def test_starts_with_an_empty_non_durable_trail():
    assert trail(client_for("hospital-a")) == {
        "node_ref": "node-hospital-a",
        "organization_ref": "org-hospital-a",
        "durable": False,
        "events": [],
    }


def test_disclosed_query_is_audited_by_reference_only():
    client = client_for("hospital-b")
    assert ask(client).status_code == 200

    [event] = trail(client)["events"]

    assert event == {
        "event_id": event["event_id"],
        "recorded_at": DEMO_NOW.isoformat(),
        "action": "patient_history_query",
        "outcome": "disclosed",
        "query_id": DR_X_MEDICATIONS["query_id"],
        "patient_ref": "pat-a",
        "requested_by": {"organization_ref": "org-hospital-a", "actor_ref": "clin-x"},
        "purpose": "Consultation de cardiologie",
        "scope": ["medications"],
        "authorization": {"basis": "patient_access_grant", "ref": "grant-a-drx"},
        "disclosed_entry_refs": ["med-b-leila-coagulix"],
    }
    # No clinical content: the medication's code and dosage are not in the trail.
    assert "MED-COAGULIX" not in str(event)


def test_denied_query_is_audited_without_disclosure():
    client = client_for("hospital-b")
    assert ask(client, purpose="Recherche").status_code == 403

    [event] = trail(client)["events"]

    assert (event["outcome"], event["disclosed_entry_refs"]) == ("denied", [])


def test_invalid_query_is_not_audited():
    client = client_for("hospital-b")
    assert ask(client, scope=[]).status_code == 400

    assert trail(client)["events"] == []


def test_lists_newest_first_and_filters():
    client = client_for("hospital-b")
    ask(client)
    ask(client, query_id=OTHER_QUERY_ID, purpose="Recherche")

    assert [e["query_id"] for e in trail(client)["events"]] == [
        OTHER_QUERY_ID,
        DR_X_MEDICATIONS["query_id"],
    ]
    assert [e["outcome"] for e in trail(client, outcome="denied")["events"]] == [
        "denied"
    ]
    assert len(trail(client, query_id=OTHER_QUERY_ID)["events"]) == 1
    assert len(trail(client, limit=1)["events"]) == 1
    assert trail(client, patient_ref="pat-b")["events"] == []


def test_each_node_keeps_only_its_own_trail():
    hospital_a, hospital_b = client_for("hospital-a"), client_for("hospital-b")
    ask(hospital_b)

    assert trail(hospital_a)["events"] == []
    assert len(trail(hospital_b)["events"]) == 1


def test_a_restart_starts_an_empty_trail():
    ask(client_for("hospital-b"))

    assert trail(client_for("hospital-b"))["events"] == []


@pytest.mark.parametrize(
    "params, field",
    [
        ({"limit": "0"}, "limit"),
        ({"limit": "501"}, "limit"),
        ({"limit": "ten"}, "limit"),
        ({"outcome": "approved"}, "outcome"),
        ({"query_id": "not-a-uuid"}, "query_id"),
        ({"patient_ref": "Patient A"}, "patient_ref"),
        ({"since": "2026-01-01"}, "since"),
        ([("outcome", "denied"), ("outcome", "disclosed")], "outcome"),
    ],
    ids=[
        "zero-limit",
        "limit-too-high",
        "non-numeric-limit",
        "unknown-outcome",
        "bad-query-id",
        "named-patient",
        "unknown-parameter",
        "repeated-parameter",
    ],
)
def test_invalid_filter_is_a_400_problem(params, field):
    response = client_for("hospital-a").get("/v1/audit/events", params=params)

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    schema("Problem").validate(response.json())
    assert response.json()["code"] == "invalid_request"
    assert field in response.json()["detail"]


def test_audit_trail_is_read_only():
    client = client_for("hospital-a")

    assert client.post("/v1/audit/events", json={}).status_code == 405
    assert client.delete("/v1/audit/events").status_code == 405
