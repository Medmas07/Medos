"""HC-212 over HTTP: every protected route of the Governance Node, with authentication
required, against its contract. Without a session `401`, with a role that does not
grant the route's permission `403 permission_denied`, with one that does, served.
"""

import pytest
from fastapi.testclient import TestClient

from adapters.outbound.credential_file import CredentialFile
from main import create_app
from tests.conftest import DEMO_DATA
from tests.test_authentication_http import (
    AUTH,
    HASHER,
    HOSPITAL,
    RESEARCH,
    SESSION,
    SIGN_IN,
    SYNC,
    Clock,
    _load,
    bearer,
    check,
)

AUDIT = _load("governance", "governance-audit-events.v1.yaml")
LEDGER = _load("governance", "governance-ledger-proofs.v1.yaml")
# One password per fictional person, for tests only.
PEOPLE = {
    "usr-olfa": "governance_reviewer",
    "usr-mehdi": "hospital_manager",
    "usr-aymen": "researcher",
    "clin-ines": "physician",
    "clin-mariem": "nurse",
}


def body_example(contract: dict, path: str, name: str) -> dict:
    content = contract["paths"][path]["post"]["requestBody"]["content"]
    return content["application/json"]["examples"][name]["value"]


SYNC_SUBMIT = body_example(
    SYNC, "/v1/synchronization-requests", "hospitalBAsksHospitalA"
)
RESEARCH_SUBMIT = body_example(RESEARCH, "/v1/research-requests", "hypertensionStudy")
HOSPITAL_DECIDE = body_example(
    HOSPITAL,
    "/v1/hospital-applications/{application_ref}/decision",
    "approveHospitalC",
)
SYNC_DECIDE = body_example(
    SYNC, "/v1/synchronization-requests/{request_ref}/decision", "approveSync001"
)
RESEARCH_DECIDE = body_example(
    RESEARCH, "/v1/research-requests/{request_ref}/decision", "approveRar002"
)

# contract, contract path, method, URL, body, a person whose role grants it, status.
ROUTES = {
    "listHospitalApplications": (
        HOSPITAL,
        "/v1/hospital-applications",
        "get",
        "/v1/hospital-applications",
        None,
        "usr-olfa",
        200,
    ),
    "getHospitalApplication": (
        HOSPITAL,
        "/v1/hospital-applications/{application_ref}",
        "get",
        "/v1/hospital-applications/app-hospital-c",
        None,
        "usr-olfa",
        200,
    ),
    "decideHospitalApplication": (
        HOSPITAL,
        "/v1/hospital-applications/{application_ref}/decision",
        "post",
        "/v1/hospital-applications/app-hospital-c/decision",
        HOSPITAL_DECIDE,
        "usr-olfa",
        201,
    ),
    "getHospitalApproval": (
        HOSPITAL,
        "/v1/hospital-approvals/{decision_ref}",
        "get",
        "/v1/hospital-approvals/dec-hospital-a",
        None,
        "usr-olfa",
        200,
    ),
    "listSynchronizationRequests": (
        SYNC,
        "/v1/synchronization-requests",
        "get",
        "/v1/synchronization-requests",
        None,
        "usr-olfa",
        200,
    ),
    "submitSynchronizationRequest": (
        SYNC,
        "/v1/synchronization-requests",
        "post",
        "/v1/synchronization-requests",
        SYNC_SUBMIT,
        "clin-ines",
        201,
    ),
    "getSynchronizationRequest": (
        SYNC,
        "/v1/synchronization-requests/{request_ref}",
        "get",
        "/v1/synchronization-requests/sync-001",
        None,
        "usr-olfa",
        200,
    ),
    "decideSynchronizationRequest": (
        SYNC,
        "/v1/synchronization-requests/{request_ref}/decision",
        "post",
        "/v1/synchronization-requests/sync-001/decision",
        SYNC_DECIDE,
        "usr-olfa",
        201,
    ),
    "listResearchRequests": (
        RESEARCH,
        "/v1/research-requests",
        "get",
        "/v1/research-requests",
        None,
        "usr-olfa",
        200,
    ),
    "submitResearchRequest": (
        RESEARCH,
        "/v1/research-requests",
        "post",
        "/v1/research-requests",
        RESEARCH_SUBMIT,
        "usr-aymen",
        201,
    ),
    "getResearchRequest": (
        RESEARCH,
        "/v1/research-requests/{request_ref}",
        "get",
        "/v1/research-requests/rar-002",
        None,
        "usr-olfa",
        200,
    ),
    "decideResearchRequest": (
        RESEARCH,
        "/v1/research-requests/{request_ref}/decision",
        "post",
        "/v1/research-requests/rar-002/decision",
        RESEARCH_DECIDE,
        "usr-olfa",
        201,
    ),
    "listGovernanceAuditEvents": (
        AUDIT,
        "/v1/audit/events",
        "get",
        "/v1/audit/events",
        None,
        "usr-olfa",
        200,
    ),
    "getGovernanceAuditEvent": (
        AUDIT,
        "/v1/audit/events/{event_ref}",
        "get",
        "/v1/audit/events/evt-004",
        None,
        "usr-olfa",
        200,
    ),
    "listLedgerProofs": (
        LEDGER,
        "/v1/ledger/proofs",
        "get",
        "/v1/ledger/proofs",
        None,
        "usr-olfa",
        200,
    ),
    "getLedgerProof": (
        LEDGER,
        "/v1/audit/events/{event_ref}/proof",
        "get",
        "/v1/audit/events/evt-004/proof",
        None,
        "usr-olfa",
        200,
    ),
}


@pytest.fixture
def client() -> TestClient:
    credentials = CredentialFile({p: HASHER.hash(f"{p}-pass") for p in PEOPLE})
    app = create_app(
        demo_data=DEMO_DATA, clock=Clock(), credentials=credentials, hasher=HASHER
    )
    return TestClient(app)


def token(client, person_ref: str) -> str:
    response = client.post(
        "/v1/auth/sessions",
        json={"person_ref": person_ref, "password": f"{person_ref}-pass"},
    )
    return response.json()["session_token"]


def call(client, operation_id: str, headers=None, **changes):
    _, _, method, url, body, _, _ = ROUTES[operation_id]
    if body is None:
        return client.request(method, url, headers=headers or {})
    return client.request(method, url, json={**body, **changes}, headers=headers or {})


def operation(operation_id: str) -> tuple[dict, dict]:
    contract, path, method, *_ = ROUTES[operation_id]
    return contract, contract["paths"][path][method]


def outsider(operation_id: str) -> str:
    """Someone signed in whose role does not grant the route."""
    return "usr-aymen" if ROUTES[operation_id][5] != "usr-aymen" else "usr-olfa"


@pytest.mark.parametrize("operation_id", ROUTES)
def test_without_a_session_a_protected_route_answers_401(client, operation_id):
    contract, op = operation(operation_id)

    response = call(client, operation_id)

    assert check(response, contract, op, 401)["code"] == "authentication_required"
    assert response.headers["www-authenticate"] == 'Bearer realm="governance-node"'


@pytest.mark.parametrize("operation_id", ROUTES)
def test_a_role_that_does_not_grant_the_route_answers_403(client, operation_id):
    contract, op = operation(operation_id)
    headers = bearer(token(client, outsider(operation_id)))

    body = check(call(client, operation_id, headers), contract, op, 403)

    assert body["code"] == "permission_denied"


@pytest.mark.parametrize("operation_id", ROUTES)
def test_a_role_that_grants_the_route_is_served(client, operation_id):
    contract, op = operation(operation_id)
    *_, person_ref, status = ROUTES[operation_id]

    check(
        call(client, operation_id, bearer(token(client, person_ref))),
        contract,
        op,
        status,
    )


@pytest.mark.parametrize("operation_id", ROUTES)
def test_a_nurse_is_granted_nothing_here(client, operation_id):
    contract, op = operation(operation_id)
    headers = bearer(token(client, "clin-mariem"))

    assert check(call(client, operation_id, headers), contract, op, 403)["code"] == (
        "permission_denied"
    )


def test_permission_is_checked_before_anything_is_looked_up(client):
    # A role without review cannot learn which applications exist.
    contract, op = operation("getHospitalApplication")
    headers = bearer(token(client, "usr-aymen"))

    response = client.get("/v1/hospital-applications/app-unknown", headers=headers)

    assert check(response, contract, op, 403)["code"] == "permission_denied"


@pytest.mark.parametrize(
    ("operation_id", "person_ref"),
    [
        ("submitSynchronizationRequest", "usr-mehdi"),
        ("submitResearchRequest", "usr-aymen"),
    ],
)
def test_a_submission_is_recorded_under_the_signed_in_person(
    client, operation_id, person_ref
):
    contract, op = operation(operation_id)
    headers = bearer(token(client, person_ref))

    body = check(
        call(client, operation_id, headers, submitted_by_ref=person_ref),
        contract,
        op,
        201,
    )

    assert body["submitted_by_ref"] == person_ref


@pytest.mark.parametrize(
    ("operation_id", "person_ref", "declared"),
    [
        ("submitSynchronizationRequest", "usr-mehdi", "clin-ines"),
        ("submitResearchRequest", "usr-aymen", "usr-mehdi"),
    ],
)
def test_a_submission_declaring_someone_else_answers_403(
    client, operation_id, person_ref, declared
):
    contract, op = operation(operation_id)
    headers = bearer(token(client, person_ref))

    response = call(client, operation_id, headers, submitted_by_ref=declared)

    body = check(response, contract, op, 403)
    assert body["code"] == "submitter_mismatch"
    assert body["detail"] == (
        f"submitted_by_ref {declared} is not the signed-in person {person_ref}."
    )


@pytest.mark.parametrize(
    ("person_ref", "permissions"),
    [
        ("usr-olfa", ["governance:audit", "governance:review"]),
        ("usr-mehdi", ["synchronization:request"]),
        ("clin-ines", ["synchronization:request"]),
        ("usr-aymen", ["research:request"]),
        ("clin-mariem", []),
    ],
)
def test_the_session_lists_what_the_role_grants(client, person_ref, permissions):
    signed_in = client.post(
        "/v1/auth/sessions",
        json={"person_ref": person_ref, "password": f"{person_ref}-pass"},
    )
    assert check(signed_in, AUTH, SIGN_IN, 201)["permissions"] == permissions

    session = client.get(
        "/v1/auth/session", headers=bearer(signed_in.json()["session_token"])
    )
    assert check(session, AUTH, SESSION["get"], 200)["permissions"] == permissions


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/health"),
        ("get", "/v1/policies"),
        ("get", "/v1/policies/pol-governance-v1"),
    ],
)
def test_health_and_the_published_policies_stay_open(client, method, url):
    assert client.request(method, url).status_code == 200


def test_the_service_authorization_checks_stay_unauthenticated(client):
    # Service-to-service authentication is HC-214's subject, not a person's role.
    sync = client.post(
        "/v1/synchronization-authorizations/dec-sync-002/checks",
        json={
            "requester_organization_ref": "org-private-practice",
            "target_organization_ref": "org-hospital-b",
            "patient_ref": "pat-c",
            "requested_scope": ["medications"],
        },
    )
    research = client.post(
        "/v1/research-authorizations/check", json={"decision_ref": "dec-unknown"}
    )

    assert sync.status_code not in (401, 403)
    assert research.status_code not in (401, 403)


def test_with_authentication_off_nothing_is_checked():
    off = TestClient(create_app(demo_data=DEMO_DATA, clock=Clock()))

    for operation_id in ROUTES:
        *_, status = ROUTES[operation_id]
        assert call(off, operation_id).status_code == status, operation_id
