"""HC-215 over HTTP: with authentication required, sign-ins and each 403 of a signed-in
person are recorded in the governance audit trail, against
contracts/api/governance/governance-audit-events.v1.yaml 1.2.0. A request without a
valid session is not recorded, and nothing is recorded with authentication off.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from adapters.outbound.credential_file import CredentialFile
from main import create_app
from tests.conftest import DEMO_DATA
from tests.test_access_control_http import PEOPLE, call, token
from tests.test_audit_http import AUDIT, LIST
from tests.test_authentication_http import HASHER, Clock, bearer
from tests.test_synchronization_http import check, example


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(clock) -> TestClient:
    credentials = CredentialFile({p: HASHER.hash(f"{p}-pass") for p in PEOPLE})
    return TestClient(
        create_app(
            demo_data=DEMO_DATA, clock=clock, credentials=credentials, hasher=HASHER
        )
    )


def security_events(client, olfa: str) -> list[dict]:
    response = client.get("/v1/audit/events?domain=security", headers=bearer(olfa))
    return check(response, AUDIT, LIST, 200)["events"]


def sign_in(client, person_ref: str, password: str):
    return client.post(
        "/v1/auth/sessions", json={"person_ref": person_ref, "password": password}
    )


def test_the_security_example_is_what_the_node_records(client, clock):
    assert sign_in(client, "usr-olfa", "wrong-password").status_code == 401
    clock.now += timedelta(minutes=1)
    olfa = token(client, "usr-olfa")
    clock.now += timedelta(minutes=1)
    aymen = token(client, "usr-aymen")
    clock.now += timedelta(minutes=1)
    assert client.get("/v1/audit/events", headers=bearer(aymen)).status_code == 403

    response = client.get("/v1/audit/events?domain=security", headers=bearer(olfa))

    assert check(response, AUDIT, LIST, 200) == example(AUDIT, LIST, 200, "security")


@pytest.mark.parametrize(
    ("operation_id", "person_ref", "changes", "permission", "reason"),
    [
        (
            "decideSynchronizationRequest",
            "usr-olfa",
            {"reviewer_ref": "usr-someone-else"},
            "governance:review",
            "reviewer_mismatch",
        ),
        (
            "submitResearchRequest",
            "usr-aymen",
            {"submitted_by_ref": "usr-mehdi"},
            "research:request",
            "submitter_mismatch",
        ),
        (
            "submitSynchronizationRequest",
            "usr-mehdi",
            {
                "submitted_by_ref": "usr-mehdi",
                "requester_organization_ref": "org-hospital-b",
            },
            "synchronization:request",
            "organization_mismatch",
        ),
    ],
)
def test_a_mismatch_is_recorded_as_answered(
    client, operation_id, person_ref, changes, permission, reason
):
    headers = bearer(token(client, person_ref))

    response = call(client, operation_id, headers, **changes)

    assert response.json()["code"] == reason
    latest = security_events(client, token(client, "usr-olfa"))[1]
    assert (latest["action"], latest["actor_ref"]) == ("access_denied", person_ref)
    assert (latest["subject_ref"], latest["reason"]) == (permission, reason)
    # Never the request's content.
    for value in changes.values():
        if value != person_ref:
            assert value not in str(latest)


@pytest.mark.parametrize(
    "headers", [{}, bearer("not-a-session"), {"Authorization": "Basic x"}]
)
def test_a_request_without_a_valid_session_is_not_recorded(client, headers):
    assert client.get("/v1/audit/events", headers=headers).status_code == 401

    # Only the reader's own sign-in.
    assert [
        e["action"] for e in security_events(client, token(client, "usr-olfa"))
    ] == ["signed_in"]


def test_a_lockout_is_recorded_once(client):
    for _ in range(7):
        assert sign_in(client, "usr-mehdi", "wrong-password").status_code == 401
    assert sign_in(client, "usr-nobody", "wrong-password").status_code == 401

    events = security_events(client, token(client, "usr-olfa"))[1:]

    assert [(e["subject_ref"], e["reason"]) for e in reversed(events)] == [
        ("usr-mehdi", "invalid_credentials")
    ] * 4 + [("usr-mehdi", "account_locked")]


def test_with_authentication_off_nothing_is_recorded():
    client = TestClient(create_app(demo_data=DEMO_DATA, clock=Clock()))

    assert client.get("/v1/audit/events?domain=security").json()["events"] == []
