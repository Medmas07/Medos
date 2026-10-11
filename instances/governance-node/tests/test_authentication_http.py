"""HC-211 over HTTP: contracts/api/auth/authentication.v1.yaml, and the decision
routes of the three governance decision contracts with authentication required.

Every response is checked against its contract schema for its status.
"""

from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from adapters.outbound.credential_file import CredentialFile
from adapters.outbound.scrypt_password_hasher import ScryptPasswordHasher
from main import create_app
from tests.conftest import DEMO_DATA, DEMO_NOW

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "api"


def _load(*parts: str) -> dict:
    return yaml.safe_load((CONTRACTS.joinpath(*parts)).read_text(encoding="utf-8"))


AUTH = _load("auth", "authentication.v1.yaml")
HOSPITAL = _load("governance", "hospital-approval.v1.yaml")
SYNC = _load("governance", "synchronization-requests.v1.yaml")
RESEARCH = _load("governance", "research-requests.v1.yaml")
SIGN_IN = AUTH["paths"]["/v1/auth/sessions"]["post"]
SESSION = AUTH["paths"]["/v1/auth/session"]
DECISIONS = {
    # contract, its decision path, the decision URL, the request example to send:
    # one decision awaiting review of each kind in the demo data.
    "hospital": (
        HOSPITAL,
        "/v1/hospital-applications/{application_ref}/decision",
        "/v1/hospital-applications/app-hospital-c/decision",
        "approveHospitalC",
    ),
    "sync": (
        SYNC,
        "/v1/synchronization-requests/{request_ref}/decision",
        "/v1/synchronization-requests/sync-001/decision",
        "approveSync001",
    ),
    "research": (
        RESEARCH,
        "/v1/research-requests/{request_ref}/decision",
        "/v1/research-requests/rar-002/decision",
        "approveRar002",
    ),
}
PASSWORD = "olfa-test-password"
HASHER = ScryptPasswordHasher(cost=(2**4, 8, 1))


def check(response, contract: dict, operation: dict, status: int) -> dict:
    assert response.status_code == status, response.text
    spec = operation["responses"][str(status)]
    if "$ref" in spec:
        spec = contract["components"]["responses"][spec["$ref"].split("/")[-1]]
    media_type, content = next(iter(spec["content"].items()))
    assert response.headers["content-type"].startswith(media_type)
    schema = {**content["schema"], "components": contract["components"]}
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
    credentials = CredentialFile(
        {"usr-olfa": HASHER.hash(PASSWORD), "usr-mehdi": HASHER.hash("mehdi-pass")}
    )
    app = create_app(
        demo_data=DEMO_DATA, clock=clock, credentials=credentials, hasher=HASHER
    )
    return TestClient(app)


def sign_in(client, person_ref="usr-olfa", password=PASSWORD):
    return client.post(
        "/v1/auth/sessions", json={"person_ref": person_ref, "password": password}
    )


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def token(client, person_ref="usr-olfa", password=PASSWORD) -> str:
    return sign_in(client, person_ref, password).json()["session_token"]


def decide_op(kind: str) -> tuple[dict, dict]:
    contract, path, _, _ = DECISIONS[kind]
    return contract, contract["paths"][path]["post"]


def decide(client, kind: str, headers=None, **changes):
    _, operation = decide_op(kind)
    url, example = DECISIONS[kind][2:]
    content = operation["requestBody"]["content"]["application/json"]
    body = {**content["examples"][example]["value"], **changes}
    return client.post(url, json=body, headers=headers or {})


# Sign-in, session, sign-out


def test_sign_in_returns_a_bearer_session_not_to_be_cached(client):
    response = sign_in(client)
    body = check(response, AUTH, SIGN_IN, 201)

    assert response.headers["cache-control"] == "no-store"
    assert body["token_type"] == "Bearer"
    assert len(body["session_token"]) >= 32
    assert (body["person_ref"], body["role"], body["organization_ref"]) == (
        "usr-olfa",
        "governance_reviewer",
        "org-governance",
    )
    assert body["issued_at"] == DEMO_NOW.isoformat()
    assert body["expires_at"] == (DEMO_NOW + timedelta(hours=8)).isoformat()


def test_each_sign_in_gets_its_own_token(client):
    assert token(client) != token(client)


@pytest.mark.parametrize(
    ("person_ref", "password"),
    [("usr-olfa", "wrong-password"), ("usr-aymen", PASSWORD), ("usr-nobody", "x")],
)
def test_a_refused_sign_in_gives_one_answer(client, person_ref, password):
    body = check(sign_in(client, person_ref, password), AUTH, SIGN_IN, 401)

    assert body["code"] == "authentication_failed"
    assert body["detail"] == (
        "Sign-in refused: unknown person, wrong password, or too many failed attempts."
    )


def test_five_failures_lock_the_account_for_fifteen_minutes(client, clock):
    for _ in range(5):
        assert sign_in(client, password="wrong-password").status_code == 401

    assert sign_in(client).status_code == 401
    clock.now += timedelta(minutes=15)
    assert sign_in(client).status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {"person_ref": "usr-olfa"},
        {"person_ref": "usr-olfa", "password": ""},
        {"person_ref": "usr olfa", "password": "x"},
        {"person_ref": "usr-olfa", "password": "x", "role": "governance_reviewer"},
        {"person_ref": "usr-olfa", "password": "x" * 1025},
    ],
)
def test_a_malformed_sign_in_is_invalid(client, body):
    response = client.post("/v1/auth/sessions", json=body)

    assert check(response, AUTH, SIGN_IN, 400)["code"] == "invalid_request"


def test_the_session_names_its_person_but_never_its_token(client):
    session_token = token(client)
    response = client.get("/v1/auth/session", headers=bearer(session_token))
    body = check(response, AUTH, SESSION["get"], 200)

    assert response.headers["cache-control"] == "no-store"
    assert body["person_ref"] == "usr-olfa"
    assert session_token not in response.text


@pytest.mark.parametrize(
    ("headers", "challenge"),
    [
        ({}, 'Bearer realm="governance-node"'),
        (
            bearer("not-a-session"),
            'Bearer realm="governance-node", error="invalid_token"',
        ),
        (
            {"Authorization": "Basic dXNyLW9sZmE6eA=="},
            'Bearer realm="governance-node", error="invalid_token"',
        ),
    ],
)
def test_no_valid_session_is_401_with_a_bearer_challenge(client, headers, challenge):
    response = client.get("/v1/auth/session", headers=headers)

    assert check(response, AUTH, SESSION["get"], 401)["code"] == (
        "authentication_required"
    )
    assert response.headers["www-authenticate"] == challenge


def test_a_session_expires_after_eight_hours(client, clock):
    session_token = token(client)
    clock.now += timedelta(hours=8)

    response = client.get("/v1/auth/session", headers=bearer(session_token))

    assert check(response, AUTH, SESSION["get"], 401)["detail"] == (
        "The session has expired."
    )


def test_sign_out_ends_the_session(client):
    session_token = token(client)

    response = client.delete("/v1/auth/session", headers=bearer(session_token))

    assert response.status_code == 204
    assert (
        client.get("/v1/auth/session", headers=bearer(session_token)).status_code == 401
    )
    again = client.delete("/v1/auth/session", headers=bearer(session_token))
    check(again, AUTH, SESSION["delete"], 401)


# Decisions with authentication required


@pytest.mark.parametrize("kind", DECISIONS)
def test_a_decision_without_a_session_is_401(client, kind):
    contract, operation = decide_op(kind)
    response = decide(client, kind)

    assert check(response, contract, operation, 401)["code"] == (
        "authentication_required"
    )
    assert response.headers["www-authenticate"].startswith("Bearer")


@pytest.mark.parametrize("kind", DECISIONS)
def test_a_decision_by_someone_else_than_the_signed_in_person_is_403(client, kind):
    contract, operation = decide_op(kind)
    response = decide(client, kind, bearer(token(client)), reviewer_ref="usr-mehdi")

    assert check(response, contract, operation, 403)["code"] == "reviewer_mismatch"


@pytest.mark.parametrize("kind", DECISIONS)
def test_the_signed_in_reviewer_decides(client, kind):
    contract, operation = decide_op(kind)
    response = decide(client, kind, bearer(token(client)))

    assert check(response, contract, operation, 201)["decided_by_ref"] == "usr-olfa"


def test_signing_in_does_not_make_someone_a_reviewer(client):
    # Authentication says who calls; the review rules still decide who may decide.
    mehdi = token(client, "usr-mehdi", "mehdi-pass")
    contract, operation = decide_op("hospital")

    response = decide(client, "hospital", bearer(mehdi), reviewer_ref="usr-mehdi")

    assert check(response, contract, operation, 403)["code"] == "reviewer_not_allowed"


def test_reads_stay_open(client):
    assert client.get("/v1/hospital-applications").status_code == 200


def test_health_reports_authentication_required(client):
    assert client.get("/health").json()["authentication"] == "required"


def test_serves_the_authentication_routes_only_when_required(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {"/v1/auth/sessions", "/v1/auth/session"} <= paths

    off = TestClient(create_app(demo_data=DEMO_DATA, clock=lambda: DEMO_NOW))
    assert not any(
        p.startswith("/v1/auth") for p in off.get("/openapi.json").json()["paths"]
    )
    assert off.post("/v1/auth/sessions", json={}).status_code == 404
