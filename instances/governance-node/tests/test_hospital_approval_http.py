"""The hospital approval API against contracts/api/governance/hospital-approval.v1.yaml.

Every response is checked against the contract schema for its status, and the
contract's examples are the expected answers on the demo data.
"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from main import create_app
from tests.conftest import DEMO_DATA, DEMO_NOW

CONTRACT = yaml.safe_load(
    (
        Path(__file__).resolve().parents[3]
        / "contracts"
        / "api"
        / "governance"
        / "hospital-approval.v1.yaml"
    ).read_text(encoding="utf-8")
)
PATHS = CONTRACT["paths"]
LIST = PATHS["/v1/hospital-applications"]["get"]
DETAIL = PATHS["/v1/hospital-applications/{application_ref}"]["get"]
DECIDE = PATHS["/v1/hospital-applications/{application_ref}/decision"]["post"]
APPROVAL = PATHS["/v1/hospital-approvals/{decision_ref}"]["get"]
APPROVE_C = DECIDE["requestBody"]["content"]["application/json"]["examples"][
    "approveHospitalC"
]["value"]


def response_spec(operation: dict, status: int) -> dict:
    spec = operation["responses"][str(status)]
    if "$ref" in spec:
        spec = CONTRACT["components"]["responses"][spec["$ref"].split("/")[-1]]
    return spec


def example(operation: dict, status: int, name: str) -> dict:
    content = response_spec(operation, status)["content"]
    return next(iter(content.values()))["examples"][name]["value"]


def check(response, operation: dict, status: int) -> dict:
    """The response has this status, its media type, and matches its schema."""
    assert response.status_code == status, response.text
    content = response_spec(operation, status)["content"]
    media_type = next(iter(content))
    assert response.headers["content-type"].startswith(media_type)
    schema = {**content[media_type]["schema"], "components": CONTRACT["components"]}
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            response.json()
        )
    )
    assert not errors, errors[0].message
    return response.json()


@pytest.fixture
def client() -> TestClient:
    # A fresh app per test: each keeps its own decisions in memory.
    return TestClient(create_app(demo_data=DEMO_DATA, clock=lambda: DEMO_NOW))


def decide(client: TestClient, application_ref: str, **changes):
    return client.post(
        f"/v1/hospital-applications/{application_ref}/decision",
        json={**APPROVE_C, **changes},
    )


def test_lists_the_application_awaiting_review(client):
    body = check(client.get("/v1/hospital-applications?status=human_review"), LIST, 200)

    assert body == example(LIST, 200, "awaitingReview")


def test_lists_every_application_review_first(client):
    body = check(client.get("/v1/hospital-applications"), LIST, 200)

    # Awaiting review first, then the approved ones, newest submission first.
    assert [a["application_ref"] for a in body["applications"]] == [
        "app-hospital-c",
        "app-private-practice",
        "app-hospital-b",
        "app-hospital-a",
    ]


def test_a_filter_without_match_is_empty(client):
    body = check(client.get("/v1/hospital-applications?status=rejected"), LIST, 200)

    assert body == example(LIST, 200, "empty")


def test_an_unknown_status_is_invalid(client):
    body = check(client.get("/v1/hospital-applications?status=lost"), LIST, 400)

    assert body["code"] == "invalid_request"


def test_reads_hospital_c_with_its_findings(client):
    body = check(client.get("/v1/hospital-applications/app-hospital-c"), DETAIL, 200)

    assert body == example(DETAIL, 200, "hospitalC")


def test_reads_a_decided_application_with_its_decision(client):
    body = check(client.get("/v1/hospital-applications/app-hospital-b"), DETAIL, 200)

    assert body["decision"] == example(APPROVAL, 200, "hospitalB")


def test_an_unknown_application_is_not_found(client):
    body = check(client.get("/v1/hospital-applications/app-unknown"), DETAIL, 404)

    assert body == example(DETAIL, 404, "notFound")


def test_approves_hospital_c_and_every_view_follows(client):
    decision = check(decide(client, "app-hospital-c"), DECIDE, 201)

    assert decision == example(DECIDE, 201, "approved")
    detail = check(client.get("/v1/hospital-applications/app-hospital-c"), DETAIL, 200)
    assert (detail["status"], detail["decision_ref"]) == ("approved", "dec-hospital-c")
    assert detail["decision"] == decision
    approval = check(client.get("/v1/hospital-approvals/dec-hospital-c"), APPROVAL, 200)
    assert approval == decision
    awaiting = client.get("/v1/hospital-applications?status=human_review").json()
    assert awaiting["applications"] == []


def test_rejects_hospital_c(client):
    decision = check(
        decide(
            client,
            "app-hospital-c",
            outcome="rejected",
            rationale="Attestation d'assurance absente à ce jour.",
            conditions=[],
        ),
        DECIDE,
        201,
    )

    assert (decision["outcome"], decision["conditions"]) == ("rejected", [])


def test_a_second_decision_conflicts(client):
    check(decide(client, "app-hospital-c"), DECIDE, 201)

    body = check(
        decide(client, "app-hospital-c", outcome="rejected", conditions=[]), DECIDE, 409
    )

    assert body["code"] == "not_awaiting_review"
    assert client.get("/v1/hospital-approvals/dec-hospital-c").json()["outcome"] == (
        "approved"
    )


def test_an_already_approved_application_conflicts(client):
    body = check(decide(client, "app-hospital-a"), DECIDE, 409)

    assert body == example(DECIDE, 409, "alreadyDecided")


def test_the_applicant_manager_may_not_decide(client):
    body = check(
        decide(client, "app-hospital-c", reviewer_ref="usr-mehdi"), DECIDE, 403
    )

    assert body == example(DECIDE, 403, "hospitalManager")


@pytest.mark.parametrize("reviewer_ref", ["clin-x", "usr-unknown", "pat-a"])
def test_other_people_may_not_decide(client, reviewer_ref):
    body = check(
        decide(client, "app-hospital-c", reviewer_ref=reviewer_ref), DECIDE, 403
    )

    assert body["code"] == "reviewer_not_allowed"


def test_lists_every_broken_rule(client):
    body = check(
        decide(client, "app-hospital-c", conditions=[], findings_acknowledged=False),
        DECIDE,
        422,
    )

    assert body == example(DECIDE, 422, "unacknowledgedFindings")
    # Nothing was recorded.
    assert client.get("/v1/hospital-approvals/dec-hospital-c").status_code == 404


def test_deciding_an_unknown_application_is_not_found(client):
    body = check(decide(client, "app-unknown"), DECIDE, 404)

    assert body["code"] == "application_not_found"


def test_a_bad_outcome_is_invalid(client):
    body = check(decide(client, "app-hospital-c", outcome="approve"), DECIDE, 400)

    assert body == {**example(DECIDE, 400, "invalid"), "detail": body["detail"]}
    assert body["detail"].startswith("outcome:")


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b"{}",
        b'{"reviewer_ref": "usr-olfa"}',
    ],
)
def test_malformed_bodies_are_invalid(client, payload):
    response = client.post(
        "/v1/hospital-applications/app-hospital-c/decision",
        content=payload,
        headers={"content-type": "application/json"},
    )

    assert check(response, DECIDE, 400)["code"] == "invalid_request"


@pytest.mark.parametrize(
    "changes",
    [
        {"findings_acknowledged": "yes"},
        {"conditions": "Une seule condition"},
        {"conditions": ["x"] * 11},
        {"rationale": "x" * 2001},
        {"reviewer_ref": "usr olfa"},
        {"extra": True},
    ],
)
def test_fields_outside_the_contract_are_invalid(client, changes):
    assert check(decide(client, "app-hospital-c", **changes), DECIDE, 400)["code"] == (
        "invalid_request"
    )


def test_reads_the_approval_hospital_b_registration_cites(client):
    body = check(client.get("/v1/hospital-approvals/dec-hospital-b"), APPROVAL, 200)

    assert body == example(APPROVAL, 200, "hospitalB")


@pytest.mark.parametrize("decision_ref", ["dec-sync-002", "dec-unknown"])
def test_other_decisions_are_not_hospital_approvals(client, decision_ref):
    body = check(client.get(f"/v1/hospital-approvals/{decision_ref}"), APPROVAL, 404)

    assert body["code"] == "decision_not_found"
    if decision_ref == "dec-sync-002":
        assert body == example(APPROVAL, 404, "notFound")
