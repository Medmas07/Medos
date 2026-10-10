"""The research APIs against their contracts.

contracts/api/governance/research-requests.v1.yaml (requests and decisions) and
contracts/api/research/research-authorization-check.v1.yaml (the Research Service's
check). Every response is checked against the contract schema for its status, and the
contracts' examples are the expected answers on the demo data.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_synchronization_http import Clock, check, example, load, request_example

REQ = load("api/governance/research-requests.v1.yaml")
AUTH = load("api/research/research-authorization-check.v1.yaml")
REQUESTS = REQ["paths"]["/v1/research-requests"]
LIST, SUBMIT = REQUESTS["get"], REQUESTS["post"]
DETAIL = REQ["paths"]["/v1/research-requests/{request_ref}"]["get"]
DECIDE = REQ["paths"]["/v1/research-requests/{request_ref}/decision"]["post"]
CHECK = AUTH["paths"]["/v1/research-authorizations/check"]["post"]

NEW = request_example(SUBMIT, "hypertensionStudy")
APPROVE_002 = request_example(DECIDE, "approveRar002")
JOB_001 = request_example(CHECK, "job001")


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(clock) -> TestClient:
    return TestClient(create_app(demo_data=DEMO_DATA, clock=clock))


def decide(client, request_ref: str, **changes):
    return client.post(
        f"/v1/research-requests/{request_ref}/decision", json={**APPROVE_002, **changes}
    )


def ask(client, **changes):
    return client.post("/v1/research-authorizations/check", json={**JOB_001, **changes})


def test_lists_the_demo_requests(client):
    body = check(client.get("/v1/research-requests"), REQ, LIST, 200)

    assert body == example(REQ, LIST, 200, "demo")
    assert check(client.get("/v1/research-requests?status=x"), REQ, LIST, 400)[
        "code"
    ] == ("invalid_request")


def test_reads_rar_002_with_its_checks(client):
    body = check(client.get("/v1/research-requests/rar-002"), REQ, DETAIL, 200)

    assert body == example(REQ, DETAIL, 200, "rar002")


def test_reads_rar_001_with_its_authorization(client):
    body = check(client.get("/v1/research-requests/rar-001"), REQ, DETAIL, 200)

    assert body["decision"]["approved_variables"] == [
        "age_band",
        "sex",
        "hba1c",
        "treated_hypertension",
    ]
    assert body["data_scope"]["population"] == {
        "age_min": 40,
        "age_max": 79,
        "encounter_from": "2024-01-01",
        "encounter_to": "2026-12-31",
    }


def test_an_unknown_request_is_not_found(client):
    assert check(
        client.get("/v1/research-requests/rar-999"), REQ, DETAIL, 404
    ) == example(REQ, DETAIL, 404, "notFound")


def test_submits_a_request(client):
    body = check(client.post("/v1/research-requests", json=NEW), REQ, SUBMIT, 201)

    assert body == example(REQ, SUBMIT, 201, "submitted")


@pytest.mark.parametrize(
    "changes",
    [
        {"data_scope": {"population": {"age_min": 50}, "variables": []}},
        {"data_scope": {"population": {}, "variables": ["age_band"]}},
        {
            "data_scope": {
                "population": {"age_min": 80, "age_max": 50},
                "variables": ["age_band"],
            }
        },
        {"data_scope": {"population": {"age_min": "50"}, "variables": ["age_band"]}},
        {"data_scope": {"population": {"age_min": 50}, "variables": ["HbA1c %"]}},
        {"participating_organization_refs": []},
        {"principal_investigator_ref": "Dr Aymen"},
        {"project_title": "  "},
        {"extra": True},
    ],
)
def test_malformed_submissions_are_invalid(client, changes):
    body = check(
        client.post("/v1/research-requests", json={**NEW, **changes}), REQ, SUBMIT, 400
    )

    assert body["code"] == "invalid_request"
    if changes == {"data_scope": {"population": {"age_min": 50}, "variables": []}}:
        assert body == example(REQ, SUBMIT, 400, "invalid")


def test_approves_rar_002_narrowed(client):
    decision = check(decide(client, "rar-002"), REQ, DECIDE, 201)

    assert decision == example(REQ, DECIDE, 201, "approved")
    detail = client.get("/v1/research-requests/rar-002").json()
    assert (detail["status"], detail["decision"]) == ("authorized", decision)


def test_an_approval_cannot_widen(client):
    body = check(
        decide(
            client,
            "rar-002",
            approved_variables=["age_band", "diagnosis"],
            minimum_cell_size=5,
        ),
        REQ,
        DECIDE,
        422,
    )

    assert body == example(REQ, DECIDE, 422, "widened")


def test_a_request_without_approved_participant_cannot_be_approved(client):
    submitted = client.post(
        "/v1/research-requests",
        json={**NEW, "participating_organization_refs": ["org-hospital-c"]},
    ).json()

    body = check(
        decide(
            client,
            submitted["request_ref"],
            approved_organization_refs=["org-hospital-c"],
            approved_variables=["age_band"],
        ),
        REQ,
        DECIDE,
        422,
    )
    assert [i["field"] for i in body["issues"]] == [
        "checks",
        "approved_organization_refs",
    ]


def test_rejects_rar_002(client):
    decision = check(
        decide(
            client,
            "rar-002",
            outcome="rejected",
            conditions=[],
            approved_organization_refs=None,
            approved_variables=None,
            validity_months=None,
            minimum_cell_size=None,
        ),
        REQ,
        DECIDE,
        201,
    )

    assert (decision["approved_variables"], decision["valid_until"]) == ([], None)


def test_a_decided_request_conflicts(client):
    assert check(decide(client, "rar-001"), REQ, DECIDE, 409) == example(
        REQ, DECIDE, 409, "alreadyDecided"
    )


@pytest.mark.parametrize("reviewer_ref", ["usr-aymen", "clin-ines", "usr-unknown"])
def test_others_may_not_decide(client, reviewer_ref):
    body = check(decide(client, "rar-002", reviewer_ref=reviewer_ref), REQ, DECIDE, 403)

    assert body["code"] == "reviewer_not_allowed"
    if reviewer_ref == "usr-aymen":
        assert body == example(REQ, DECIDE, 403, "investigator")


@pytest.mark.parametrize(
    "changes",
    [{"validity_months": "6"}, {"approved_variables": ["HbA1c %"]}, {"outcome": "ok"}],
)
def test_malformed_decisions_are_invalid(client, changes):
    assert (
        check(decide(client, "rar-002", **changes), REQ, DECIDE, 400)["code"]
        == "invalid_request"
    )


def test_deciding_an_unknown_request_is_not_found(client):
    assert (
        check(decide(client, "rar-999"), REQ, DECIDE, 404)["code"]
        == "request_not_found"
    )


# The Research Service's check (research-authorization-check.v1.yaml)


def test_dec_rar_001_authorizes_job_001(client):
    body = check(ask(client), AUTH, CHECK, 200)

    assert body == example(AUTH, CHECK, 200, "approved")


def test_a_variable_outside_the_decision_is_denied(client):
    body = check(
        ask(
            client,
            data_scope={
                **JOB_001["data_scope"],
                "variables": ["age_band", "diagnosis"],
            },
        ),
        AUTH,
        CHECK,
        200,
    )

    assert body == example(AUTH, CHECK, 200, "denied")


@pytest.mark.parametrize(
    "changes, reason",
    [
        ({"project_ref": "proj-002"}, "project_mismatch"),
        ({"requested_by": "usr-olfa"}, "requester_mismatch"),
        (
            {"target_organization_refs": ["org-private-practice"]},
            "organization_not_approved",
        ),
        (
            {"data_scope": {"population": {"age_min": 18}, "variables": ["hba1c"]}},
            "population_exceeded",
        ),
    ],
)
def test_each_difference_is_denied(client, changes, reason):
    body = check(ask(client, **changes), AUTH, CHECK, 200)

    assert (body["status"], body["reason_code"]) == ("denied", reason)
    assert (body["approved_organization_refs"], body["approved_variables"]) == ([], [])


def test_the_authorization_ends_with_its_validity(client, clock):
    clock.now = datetime.fromisoformat("2027-07-20T15:00:00+01:00")

    body = check(ask(client), AUTH, CHECK, 200)

    assert body["reason_code"] == "expired"


def test_a_new_approval_authorizes_its_own_job(client):
    check(decide(client, "rar-002"), REQ, DECIDE, 201)

    body = check(
        ask(
            client,
            decision_ref="dec-rar-002",
            project_ref="proj-002",
            target_organization_refs=["org-hospital-b"],
            data_scope={
                "population": {"age_min": 18, "age_max": 30},
                "variables": ["age_band"],
            },
        ),
        AUTH,
        CHECK,
        200,
    )

    assert (body["status"], body["valid_until"]) == (
        "approved",
        "2027-04-10T10:00:00+01:00",
    )


@pytest.mark.parametrize("decision_ref", ["dec-rar-002", "dec-sync-002", "dec-unknown"])
def test_unknown_or_other_decisions_are_not_found(client, decision_ref):
    response = ask(client, decision_ref=decision_ref)

    assert response.status_code == 404
    assert response.json()["code"] == "decision_not_found"


@pytest.mark.parametrize(
    "changes",
    [
        {"target_organization_refs": []},
        {"data_scope": {"population": {}, "variables": ["hba1c"]}},
        {"purpose": ""},
        {"extra": 1},
    ],
)
def test_checks_outside_the_contract_are_invalid(client, changes):
    assert ask(client, **changes).status_code == 400


def test_demo_now_is_inside_dec_rar_001():
    assert DEMO_NOW < datetime.fromisoformat("2027-07-20T15:00:00+01:00")
