import copy
import re
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from infrastructure.config import load_config
from main import create_app
from tests.conftest import CONFIG_DIR, DEMO_NOW
from tests.test_federation_http import DR_X_MEDICATIONS

CONTRACT = yaml.safe_load(
    (
        Path(__file__).resolve().parents[3]
        / "contracts"
        / "api"
        / "patient-access"
        / "patient-access-grants.v1.yaml"
    ).read_text(encoding="utf-8")
)
GRANTS = CONTRACT["paths"]["/v1/patients/{patient_ref}/access-grants"]
REVOCATION = CONTRACT["paths"][
    "/v1/patients/{patient_ref}/access-grants/{grant_ref}/revocation"
]["post"]


def example(operation: dict, status: str, name: str) -> dict:
    return operation["responses"][status]["content"]["application/json"]["examples"][
        name
    ]["value"]


PATIENT_A_GRANTS = example(GRANTS["get"], "200", "patientA")
GRANTED = example(GRANTS["post"], "201", "granted")
REVOKED = example(REVOCATION, "200", "revoked")
# The contract's own example: Patient A grants Dr. Ines a month of medications.
INES_GRANT = GRANTS["post"]["requestBody"]["content"]["application/json"]["examples"][
    "patientAGrantsInes"
]["value"]


def schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": CONTRACT["components"]},
        format_checker=FormatChecker(),
    )


def client_for(hospital: str, **options) -> TestClient:
    # A fresh app per test: each keeps its own grants in memory.
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")
    return TestClient(create_app(config, clock=lambda: DEMO_NOW, **options))


def grants_of(patient_ref: str = "pat-a") -> str:
    return f"/v1/patients/{patient_ref}/access-grants"


def revoke(client: TestClient, grant_ref: str, patient_ref: str = "pat-a"):
    return client.post(f"{grants_of(patient_ref)}/{grant_ref}/revocation")


def problem(response, status: int, code: str) -> dict:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    schema("Problem").validate(response.json())
    assert response.json()["code"] == code
    return response.json()


def denied(response) -> bool:
    """A federation query refused under hospital-node-federation.v1."""
    return (
        response.status_code == 403
        and response.json()["code"] == "authorization_denied"
    )


def ines_asks(client: TestClient, grant_ref: str):
    """Dr. Ines asks for Patient A's medications under grant_ref."""
    body = copy.deepcopy(DR_X_MEDICATIONS)
    body["query_id"] = str(uuid.uuid4())
    body["purpose"] = INES_GRANT["purpose"]
    body["requested_by"]["actor_ref"] = "clin-ines"
    body["authorization"]["ref"] = grant_ref
    return client.post("/v1/federation/queries", json=body)


def test_lists_a_patients_grants_as_in_the_contract_example():
    response = client_for("hospital-a").get(grants_of())

    assert response.status_code == 200
    schema("AccessGrantList").validate(response.json())
    assert response.json() == PATIENT_A_GRANTS


def test_an_unknown_patient_has_no_grants():
    response = client_for("hospital-a").get(grants_of("pat-unknown"))

    assert response.json()["grants"] == []


def test_records_a_grant_as_in_the_contract_example():
    client = client_for(
        "hospital-a", new_grant_ref=lambda: GRANTED["grant"]["grant_ref"]
    )

    response = client.post(grants_of(), json=INES_GRANT)

    assert response.status_code == 201
    schema("AccessGrantRecord").validate(response.json())
    assert response.json() == GRANTED
    assert GRANTED["grant"] in client.get(grants_of()).json()["grants"]


def test_generates_an_opaque_grant_reference():
    response = client_for("hospital-a").post(grants_of(), json=INES_GRANT)

    assert re.fullmatch(r"grant-[0-9a-f]{32}", response.json()["grant"]["grant_ref"])


def test_revokes_a_grant_as_in_the_contract_example():
    client = client_for("hospital-b")

    response = revoke(client, "grant-a-drx")

    assert response.status_code == 200
    schema("AccessGrantRecord").validate(response.json())
    assert response.json() == REVOKED
    listed = {g["grant_ref"]: g for g in client.get(grants_of()).json()["grants"]}
    assert listed["grant-a-drx"]["status"] == "revoked"


def test_revoking_twice_keeps_the_first_revocation():
    client = client_for("hospital-b")
    first = revoke(client, "grant-a-drx").json()

    assert revoke(client, "grant-a-drx").json() == first


@pytest.mark.parametrize(
    "grant_ref", ["grant-unknown", "grant-b-drx"], ids=["unknown", "another-patients"]
)
def test_an_unknown_or_foreign_grant_is_not_found(grant_ref):
    problem(revoke(client_for("hospital-b"), grant_ref), 404, "grant_not_found")


def test_the_node_enforces_a_grant_from_its_recording_to_its_revocation():
    client = client_for("hospital-b")

    grant_ref = client.post(grants_of(), json=INES_GRANT).json()["grant"]["grant_ref"]
    allowed = ines_asks(client, grant_ref)
    revoke(client, grant_ref)
    refused = ines_asks(client, grant_ref)

    assert allowed.status_code == 200
    assert [e["entry_ref"] for e in allowed.json()["entries"]] == [
        "med-b-leila-coagulix"
    ]
    assert denied(refused)
    audited = client.get("/v1/audit/events", params={"patient_ref": "pat-a"}).json()
    assert [(e["authorization"]["ref"], e["outcome"]) for e in audited["events"]] == [
        (grant_ref, "denied"),
        (grant_ref, "disclosed"),
    ]


def test_a_grant_recorded_on_one_node_does_not_reach_another():
    hospital_b = client_for("hospital-b")
    grant_ref = hospital_b.post(grants_of(), json=INES_GRANT).json()["grant"][
        "grant_ref"
    ]

    assert denied(ines_asks(client_for("hospital-a"), grant_ref))


def test_revoking_the_demo_grant_denies_the_contracts_demo_query():
    client = client_for("hospital-b")
    assert client.post("/v1/federation/queries", json=DR_X_MEDICATIONS).is_success

    revoke(client, "grant-a-drx")

    assert denied(client.post("/v1/federation/queries", json=DR_X_MEDICATIONS))


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({**INES_GRANT, "expires_at": DEMO_NOW.isoformat()}, "expires_at"),
        (
            {**INES_GRANT, "expires_at": (DEMO_NOW - timedelta(days=1)).isoformat()},
            "expires_at",
        ),
        ({**INES_GRANT, "expires_at": "2026-11-10T10:00:00"}, "expires_at"),
        ({**INES_GRANT, "scope": []}, "scope"),
        ({**INES_GRANT, "scope": ["medications", "medications"]}, "scope"),
        ({**INES_GRANT, "scope": ["imaging"]}, "scope"),
        ({**INES_GRANT, "grantee_ref": "Dr Karim"}, "grantee_ref"),
        ({**INES_GRANT, "purpose": ""}, "purpose"),
        ({**INES_GRANT, "status": "active"}, "status"),
        ({k: v for k, v in INES_GRANT.items() if k != "scope"}, "scope"),
    ],
    ids=[
        "expires-now",
        "expired",
        "no-offset",
        "empty-scope",
        "repeated-scope",
        "unknown-scope",
        "non-opaque-grantee",
        "empty-purpose",
        "unknown-field",
        "missing-scope",
    ],
)
def test_a_request_outside_the_contract_is_invalid(body, field):
    client = client_for("hospital-a")

    error = problem(client.post(grants_of(), json=body), 400, "invalid_request")

    assert error["title"] == "Invalid access grant request"
    assert field in error["detail"]
    assert len(client.get(grants_of()).json()["grants"]) == 2


def test_malformed_json_is_invalid():
    response = client_for("hospital-a").post(
        grants_of(), content=b"{", headers={"content-type": "application/json"}
    )

    problem(response, 400, "invalid_request")


@pytest.mark.parametrize(
    "send",
    [
        lambda c: c.get(grants_of("-pat")),
        lambda c: c.post(grants_of("-pat"), json=INES_GRANT),
        lambda c: revoke(c, "-grant"),
    ],
    ids=["list", "grant", "revoke"],
)
def test_a_non_opaque_path_reference_is_invalid(send):
    problem(send(client_for("hospital-a")), 400, "invalid_request")
