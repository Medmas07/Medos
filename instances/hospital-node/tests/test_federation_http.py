import copy
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from infrastructure.config import load_config
from main import create_app
from tests.conftest import CONFIG_DIR, DEMO_NOW

CONTRACT = yaml.safe_load(
    (
        Path(__file__).resolve().parents[3]
        / "contracts"
        / "federation"
        / "hospital-node-federation.v1.yaml"
    ).read_text(encoding="utf-8")
)
QUERY_OPERATION = CONTRACT["paths"]["/v1/federation/queries"]["post"]
# The contract's own example: Dr. X asks for Patient A's medications.
DR_X_MEDICATIONS = QUERY_OPERATION["requestBody"]["content"]["application/json"][
    "examples"
]["drXPatientA"]["value"]


def schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": CONTRACT["components"]},
        format_checker=FormatChecker(),
    )


def client_for(hospital: str) -> TestClient:
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")
    return TestClient(create_app(config, clock=lambda: DEMO_NOW))


def ask(hospital: str, **changes) -> dict:
    body = copy.deepcopy(DR_X_MEDICATIONS) | changes
    return client_for(hospital).post("/v1/federation/queries", json=body)


def entry_refs(response) -> set[str]:
    return {entry["entry_ref"] for entry in response.json()["entries"]}


@pytest.mark.parametrize("hospital", ["hospital-a", "hospital-b", "private-practice"])
def test_describes_the_configured_node(hospital):
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")

    response = client_for(hospital).get("/v1/federation/node")

    assert response.status_code == 200
    schema("NodeDescriptor").validate(response.json())
    assert response.json() == {
        "node_ref": config.identity.node_ref,
        "organization_ref": config.identity.organization_ref,
        "contract_versions": ["1.0"],
        "status": "online",
        "supported_scopes": ["encounters", "medications", "lab_reports"],
        "mocked": True,
    }


def test_answers_the_contract_example_with_medication_a():
    response = ask("hospital-b")

    assert response.status_code == 200
    schema("NodeQueryResult").validate(response.json())
    assert response.json() == {
        "query_id": DR_X_MEDICATIONS["query_id"],
        "contract_version": "1.0",
        "node_ref": "node-hospital-b",
        "organization_ref": "org-hospital-b",
        "patient_ref": "pat-a",
        "entries": [
            {
                "entry_ref": "med-b-leila-coagulix",
                "record_type": "medication",
                "occurred_at": "2026-05-20T00:00:00+00:00",
                "source": {
                    "organization_ref": "org-hospital-b",
                    "node_ref": "node-hospital-b",
                },
                "medication": {
                    "code": "MED-COAGULIX",
                    "dosage": "5 mg, 2 fois par jour",
                    "status": "active",
                    "start_date": "2026-05-20",
                    "end_date": None,
                    "prescribed_by_ref": "clin-ines",
                },
            }
        ],
        "provenance": {"mocked": True, "answered_at": DEMO_NOW.isoformat()},
    }


@pytest.mark.parametrize(
    "hospital, expected",
    [
        ("hospital-a", {"enc-a-2024-leila-er", "lab-a-2024-leila"}),
        (
            "hospital-b",
            {"enc-b-2026-leila", "med-b-leila-coagulix", "lab-b-2026-leila"},
        ),
        ("private-practice", {"enc-pp-2025-leila", "med-pp-leila-tensiorel"}),
    ],
)
def test_each_node_discloses_only_its_own_records_of_the_patient(hospital, expected):
    response = ask(hospital, scope=["encounters", "medications", "lab_reports"])

    assert response.status_code == 200
    schema("NodeQueryResult").validate(response.json())
    assert entry_refs(response) == expected
    organization = load_config(CONFIG_DIR / f"{hospital}.demo.json").identity
    assert {e["source"]["node_ref"] for e in response.json()["entries"]} == {
        organization.node_ref
    }


def test_returns_only_the_requested_scope():
    response = ask("hospital-b", scope=["lab_reports"])

    assert entry_refs(response) == {"lab-b-2026-leila"}


def test_nothing_in_scope_is_an_empty_answer():
    # Hospital A holds no medication for Patient A.
    nothing_in_scope = ask("hospital-a").json()

    assert nothing_in_scope["entries"] == []
    schema("NodeQueryResult").validate(nothing_in_scope)


def test_refused_query_returns_a_problem_and_no_entry():
    body = copy.deepcopy(DR_X_MEDICATIONS)
    body["authorization"]["ref"] = "grant-a-ines"

    response = client_for("hospital-b").post("/v1/federation/queries", json=body)

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    schema("Problem").validate(response.json())
    assert response.json()["code"] == "authorization_denied"
    assert "entries" not in response.json()


def test_refusal_is_the_same_for_an_unknown_patient():
    unknown = ask("hospital-b", patient_ref="pat-unknown")
    known = ask("hospital-b", purpose="Recherche")

    assert unknown.status_code == known.status_code == 403
    assert unknown.json() == known.json()


@pytest.mark.parametrize(
    "changes, field",
    [
        ({"scope": []}, "scope"),
        ({"scope": ["medications", "medications"]}, "scope"),
        ({"scope": ["imaging"]}, "scope.0"),
        ({"query_id": "not-a-uuid"}, "query_id"),
        ({"patient_ref": "Patient A"}, "patient_ref"),
        ({"purpose": ""}, "purpose"),
        ({"purpose": "   "}, "purpose"),
        ({"raw_sql": "SELECT *"}, "raw_sql"),
    ],
    ids=[
        "empty-scope",
        "duplicate-scope",
        "unknown-scope",
        "bad-query-id",
        "named-patient",
        "empty-purpose",
        "blank-purpose",
        "unknown-field",
    ],
)
def test_invalid_query_is_a_400_problem(changes, field):
    response = ask("hospital-b", **changes)

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    schema("Problem").validate(response.json())
    assert response.json()["code"] == "invalid_request"
    assert field in response.json()["detail"]


def test_missing_authorization_is_a_400_problem():
    body = {k: v for k, v in DR_X_MEDICATIONS.items() if k != "authorization"}

    response = client_for("hospital-b").post("/v1/federation/queries", json=body)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing fields: authorization"


def test_malformed_json_is_a_400_problem():
    response = client_for("hospital-b").post(
        "/v1/federation/queries",
        content=b"{not json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_query_id_is_echoed_unchanged():
    query_id = DR_X_MEDICATIONS["query_id"].upper()

    assert ask("hospital-b", query_id=query_id).json()["query_id"] == query_id
