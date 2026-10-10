"""The synchronization APIs against their contracts.

contracts/api/governance/synchronization-requests.v1.yaml (requests and decisions) and
contracts/federation/sync-authorization-check.v1.yaml (the Federation Service's check).
Every response is checked against the contract schema for its status, and the
contracts' examples are the expected answers on the demo data.
"""

from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from main import create_app
from tests.conftest import DEMO_DATA, DEMO_NOW

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"


def load(relative: str) -> dict:
    return yaml.safe_load((CONTRACTS / relative).read_text(encoding="utf-8"))


SYNC = load("api/governance/synchronization-requests.v1.yaml")
CHECK = load("federation/sync-authorization-check.v1.yaml")
REQUESTS = SYNC["paths"]["/v1/synchronization-requests"]
LIST, SUBMIT = REQUESTS["get"], REQUESTS["post"]
DETAIL = SYNC["paths"]["/v1/synchronization-requests/{request_ref}"]["get"]
DECIDE = SYNC["paths"]["/v1/synchronization-requests/{request_ref}/decision"]["post"]
CHECK_OP = CHECK["paths"]["/v1/synchronization-authorizations/{decision_ref}/checks"][
    "post"
]


def request_example(contract_op: dict, name: str) -> dict:
    return contract_op["requestBody"]["content"]["application/json"]["examples"][name][
        "value"
    ]


NEW_B = request_example(SUBMIT, "hospitalBAsksHospitalA")
APPROVE_001 = request_example(DECIDE, "approveSync001")
ASK_A = request_example(CHECK_OP, "hospitalAAsksHospitalB")


def response_spec(contract: dict, operation: dict, status: int) -> dict:
    spec = operation["responses"][str(status)]
    if "$ref" in spec:
        spec = contract["components"]["responses"][spec["$ref"].split("/")[-1]]
    return spec


def example(contract: dict, operation: dict, status: int, name: str) -> dict:
    content = response_spec(contract, operation, status)["content"]
    return next(iter(content.values()))["examples"][name]["value"]


def check(response, contract: dict, operation: dict, status: int) -> dict:
    assert response.status_code == status, response.text
    content = response_spec(contract, operation, status)["content"]
    media_type = next(iter(content))
    assert response.headers["content-type"].startswith(media_type)
    schema = {**content[media_type]["schema"], "components": contract["components"]}
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            response.json()
        )
    )
    assert not errors, errors[0].message
    return response.json()


class Clock:
    def __init__(self) -> None:
        self.now = DEMO_NOW

    def __call__(self):
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(clock) -> TestClient:
    # A fresh app per test: each keeps its own requests and decisions in memory.
    return TestClient(create_app(demo_data=DEMO_DATA, clock=clock))


def decide(client, request_ref: str, **changes):
    return client.post(
        f"/v1/synchronization-requests/{request_ref}/decision",
        json={**APPROVE_001, **changes},
    )


def ask(client, decision_ref: str, **changes):
    return client.post(
        f"/v1/synchronization-authorizations/{decision_ref}/checks",
        json={**ASK_A, **changes},
    )


# Requests and decisions (synchronization-requests.v1.yaml)


def test_lists_the_demo_requests_with_their_status_today(client):
    body = check(client.get("/v1/synchronization-requests"), SYNC, LIST, 200)

    assert body == example(SYNC, LIST, 200, "demo")


def test_filters_by_status(client):
    body = check(
        client.get("/v1/synchronization-requests?status=active"), SYNC, LIST, 200
    )

    assert body["requests"] == []
    assert (
        check(client.get("/v1/synchronization-requests?status=x"), SYNC, LIST, 400)[
            "code"
        ]
        == "invalid_request"
    )


def test_reads_sync_001_with_its_checks(client):
    body = check(client.get("/v1/synchronization-requests/sync-001"), SYNC, DETAIL, 200)

    assert body == example(SYNC, DETAIL, 200, "sync001")


def test_reads_a_manual_and_a_failing_consent_basis(client):
    sync_002 = check(
        client.get("/v1/synchronization-requests/sync-002"), SYNC, DETAIL, 200
    )
    sync_003 = check(
        client.get("/v1/synchronization-requests/sync-003"), SYNC, DETAIL, 200
    )

    assert sync_002["checks"][1]["state"] == "manual"
    assert sync_002["decision"]["approved_days"] == 90
    assert sync_003["checks"][1]["state"] == "fail"
    assert sync_003["decision"]["outcome"] == "rejected"


def test_an_unknown_request_is_not_found(client):
    body = check(client.get("/v1/synchronization-requests/sync-999"), SYNC, DETAIL, 404)

    assert body == example(SYNC, DETAIL, 404, "notFound")


def test_submits_a_pending_request(client):
    body = check(
        client.post("/v1/synchronization-requests", json=NEW_B), SYNC, SUBMIT, 201
    )

    assert body == example(SYNC, SUBMIT, 201, "submitted")
    pending = client.get("/v1/synchronization-requests?status=pending").json()
    assert [r["request_ref"] for r in pending["requests"]] == ["sync-004", "sync-001"]


def test_a_request_to_an_unapproved_hospital_is_recorded_but_cannot_be_approved(client):
    body = check(
        client.post(
            "/v1/synchronization-requests",
            json={**NEW_B, "target_organization_ref": "org-hospital-c"},
        ),
        SYNC,
        SUBMIT,
        201,
    )

    assert body["checks"][0]["state"] == "fail"
    refused = check(
        decide(client, body["request_ref"], approved_days=30), SYNC, DECIDE, 422
    )
    assert [i["field"] for i in refused["issues"]] == ["checks"]


@pytest.mark.parametrize(
    "changes",
    [
        {"duration_days": 366},
        {"duration_days": "30"},
        {"scope": []},
        {"scope": ["lab_reports", "lab_reports"]},
        {"scope": ["xrays"]},
        {"patient_ref": "Leïla Mansouri"},
        {"purpose": ""},
        {"consent": {"basis": "patient_grant"}},
        {"extra": 1},
    ],
)
def test_malformed_submissions_are_invalid(client, changes):
    body = check(
        client.post("/v1/synchronization-requests", json={**NEW_B, **changes}),
        SYNC,
        SUBMIT,
        400,
    )

    assert body["code"] == "invalid_request"
    if changes == {"duration_days": 366}:
        assert body == example(SYNC, SUBMIT, 400, "invalid")


@pytest.mark.parametrize(
    "changes",
    [
        {"target_organization_ref": "org-hospital-b"},
        {"consent": {"basis": "patient_grant", "access_grant_ref": None}},
        {"consent": {"basis": "none", "access_grant_ref": "grant-b-drx"}},
        {"purpose": "   "},
    ],
)
def test_incoherent_submissions_are_invalid(client, changes):
    body = check(
        client.post("/v1/synchronization-requests", json={**NEW_B, **changes}),
        SYNC,
        SUBMIT,
        400,
    )

    assert body["code"] == "invalid_request"


def test_step_20_approves_sync_001_for_13_days(client):
    decision = check(decide(client, "sync-001"), SYNC, DECIDE, 201)

    assert decision == example(SYNC, DECIDE, 201, "approved")
    detail = client.get("/v1/synchronization-requests/sync-001").json()
    assert (detail["status"], detail["valid_until"]) == (
        "active",
        decision["valid_until"],
    )
    assert detail["decision"] == decision


def test_approving_beyond_patient_a_grant_is_refused(client):
    body = check(decide(client, "sync-001", approved_days=30), SYNC, DECIDE, 422)

    assert body == example(SYNC, DECIDE, 422, "tooLong")


def test_a_signed_consent_needs_confirmation(client):
    submitted = client.post(
        "/v1/synchronization-requests",
        json={
            **NEW_B,
            "consent": {"basis": "signed_consent_form", "access_grant_ref": None},
        },
    ).json()

    refused = check(
        decide(client, submitted["request_ref"], approved_days=30), SYNC, DECIDE, 422
    )
    assert [i["field"] for i in refused["issues"]] == ["manual_checks_confirmed"]
    approved = decide(
        client, submitted["request_ref"], approved_days=30, manual_checks_confirmed=True
    )
    assert check(approved, SYNC, DECIDE, 201)["approved_days"] == 30


def test_a_decided_request_conflicts(client):
    body = check(decide(client, "sync-003"), SYNC, DECIDE, 409)

    assert body == example(SYNC, DECIDE, 409, "alreadyDecided")


@pytest.mark.parametrize("reviewer_ref", ["clin-x", "usr-mehdi", "usr-unknown"])
def test_others_may_not_decide(client, reviewer_ref):
    body = check(
        decide(client, "sync-001", reviewer_ref=reviewer_ref), SYNC, DECIDE, 403
    )

    assert body["code"] == "reviewer_not_allowed"
    if reviewer_ref == "clin-x":
        assert body == example(SYNC, DECIDE, 403, "involvedClinician")


def test_rejects_sync_001(client):
    decision = check(
        decide(client, "sync-001", outcome="rejected", approved_days=None),
        SYNC,
        DECIDE,
        201,
    )

    assert (decision["approved_days"], decision["valid_until"]) == (None, None)


@pytest.mark.parametrize(
    "changes",
    [{"approved_days": "13"}, {"manual_checks_confirmed": None}, {"outcome": "ok"}],
)
def test_malformed_decisions_are_invalid(client, changes):
    assert check(decide(client, "sync-001", **changes), SYNC, DECIDE, 400)["code"] == (
        "invalid_request"
    )


def test_deciding_an_unknown_request_is_not_found(client):
    assert check(decide(client, "sync-999"), SYNC, DECIDE, 404)["code"] == (
        "request_not_found"
    )


# The Federation Service's check (sync-authorization-check.v1.yaml)


def test_the_step_20_approval_authorizes_hospital_a(client, clock):
    check(decide(client, "sync-001"), SYNC, DECIDE, 201)
    clock.now = DEMO_NOW + timedelta(minutes=30)

    body = check(ask(client, "dec-sync-001"), CHECK, CHECK_OP, 200)

    assert body == example(CHECK, CHECK_OP, 200, "authorized")


def test_the_authorization_ends_with_its_validity(client, clock):
    decision = decide(client, "sync-001").json()
    clock.now = DEMO_NOW + timedelta(days=13)

    body = check(ask(client, "dec-sync-001"), CHECK, CHECK_OP, 200)

    assert (body["outcome"], body["reason"]) == ("denied", "expired")
    assert body["valid_until"] == decision["valid_until"]
    assert (
        client.get("/v1/synchronization-requests/sync-001").json()["status"]
        == "expired"
    )


@pytest.mark.parametrize(
    "decision_ref, name", [("dec-sync-002", "expired"), ("dec-sync-003", "rejected")]
)
def test_demo_decisions_deny(client, clock, decision_ref, name):
    clock.now = DEMO_NOW + timedelta(minutes=30)

    body = check(ask(client, decision_ref), CHECK, CHECK_OP, 200)

    assert body == example(CHECK, CHECK_OP, 200, name)


@pytest.mark.parametrize(
    "decision_ref, changes, reason",
    [
        ("dec-sync-404", {}, "not_found"),
        ("dec-hospital-a", {}, "not_found"),
        (
            "dec-sync-001",
            {"requester_organization_ref": "org-private-practice"},
            "requester_mismatch",
        ),
        ("dec-sync-001", {"patient_ref": "pat-b"}, "patient_mismatch"),
        ("dec-sync-001", {"scope": ["encounters"]}, "scope_exceeded"),
        ("dec-sync-001", {"purpose": "Étude interne"}, "purpose_mismatch"),
    ],
)
def test_each_difference_is_denied(client, decision_ref, changes, reason):
    decide(client, "sync-001")

    body = check(ask(client, decision_ref, **changes), CHECK, CHECK_OP, 200)

    assert (body["outcome"], body["reason"]) == ("denied", reason)


def test_a_pending_request_authorizes_nothing(client):
    body = check(ask(client, "dec-sync-001"), CHECK, CHECK_OP, 200)

    assert body["reason"] == "not_found"


@pytest.mark.parametrize(
    "payload, fields",
    [
        ({k: v for k, v in ASK_A.items() if k != "scope"}, "scope"),
        ({**ASK_A, "scope": []}, "scope"),
        ({**ASK_A, "actor_ref": "Dr X"}, "actor_ref"),
        ({**ASK_A, "extra": True}, "extra"),
    ],
)
def test_checks_outside_the_contract_are_invalid(client, payload, fields):
    response = client.post(
        "/v1/synchronization-authorizations/dec-sync-001/checks", json=payload
    )

    body = check(response, CHECK, CHECK_OP, 400)
    assert body["detail"] == f"Invalid or missing fields: {fields}"
    if fields == "scope" and "scope" not in payload:
        assert body == example(CHECK, CHECK_OP, 400, "invalidRequest")
