"""HC-213 over HTTP, with authentication required, against the contracts: a submission
names the signed-in person's own organization (`403 organization_mismatch` otherwise),
and a role held at an organization the Node does not recognize for it grants nothing
(`403 permission_denied`).
"""

import pytest
from fastapi.testclient import TestClient

from adapters.outbound.credential_file import CredentialFile
from domain.node_identity import NodeIdentity
from main import create_app
from tests.conftest import DEMO_DATA
from tests.test_access_control_http import (
    PEOPLE,
    ROUTES,
    call,
    operation,
    token,
)
from tests.test_authentication_http import HASHER, Clock, bearer, check


def app_client(identity: NodeIdentity | None = None) -> TestClient:
    credentials = CredentialFile({p: HASHER.hash(f"{p}-pass") for p in PEOPLE})
    options = {"identity": identity} if identity else {}
    return TestClient(
        create_app(
            demo_data=DEMO_DATA,
            clock=Clock(),
            credentials=credentials,
            hasher=HASHER,
            **options,
        )
    )


@pytest.fixture
def client() -> TestClient:
    return app_client()


@pytest.mark.parametrize(
    ("operation_id", "person_ref", "field", "declared", "own"),
    [
        # usr-mehdi manages Hospital C, not Hospital B.
        (
            "submitSynchronizationRequest",
            "usr-mehdi",
            "requester_organization_ref",
            "org-hospital-b",
            "org-hospital-c",
        ),
        (
            "submitResearchRequest",
            "usr-aymen",
            "research_organization_ref",
            "org-hospital-a",
            "org-research-lab",
        ),
    ],
)
def test_a_submission_for_another_organization_answers_403(
    client, operation_id, person_ref, field, declared, own
):
    contract, op = operation(operation_id)
    headers = bearer(token(client, person_ref))

    response = call(
        client, operation_id, headers, submitted_by_ref=person_ref, **{field: declared}
    )

    body = check(response, contract, op, 403)
    assert body["code"] == "organization_mismatch"
    assert body["detail"] == (
        f"{field} {declared} is not the signed-in person's organization {own}."
    )


def test_a_submission_for_the_signed_in_persons_organization_is_recorded(client):
    contract, op = operation("submitSynchronizationRequest")
    headers = bearer(token(client, "usr-mehdi"))

    body = check(
        call(
            client,
            "submitSynchronizationRequest",
            headers,
            submitted_by_ref="usr-mehdi",
            requester_organization_ref="org-hospital-c",
        ),
        contract,
        op,
        201,
    )

    assert body["requester_organization_ref"] == "org-hospital-c"


def test_nothing_is_recorded_for_another_organization(client):
    headers = bearer(token(client, "usr-mehdi"))
    reviewer = bearer(token(client, "usr-olfa"))
    before = client.get("/v1/synchronization-requests", headers=reviewer).json()

    call(
        client,
        "submitSynchronizationRequest",
        headers,
        submitted_by_ref="usr-mehdi",
        requester_organization_ref="org-hospital-a",
    )

    after = client.get("/v1/synchronization-requests", headers=reviewer).json()
    assert after["requests"] == before["requests"]


@pytest.mark.parametrize(
    "operation_id", [o for o in ROUTES if ROUTES[o][5] == "usr-olfa"]
)
def test_a_reviewer_of_another_authority_is_granted_nothing_here(operation_id):
    # This Node runs for another Authority than usr-olfa's org-governance.
    client = app_client(NodeIdentity("node-gov-2", "org-gov-2"))
    contract, op = operation(operation_id)
    headers = bearer(token(client, "usr-olfa"))

    body = check(call(client, operation_id, headers), contract, op, 403)

    assert body["code"] == "permission_denied"
    assert "not the Authority this Governance Node runs for" in body["detail"]


def test_with_authentication_off_the_declared_organization_is_kept():
    off = TestClient(create_app(demo_data=DEMO_DATA, clock=Clock()))

    response = call(
        off,
        "submitSynchronizationRequest",
        submitted_by_ref="usr-mehdi",
        requester_organization_ref="org-hospital-b",
    )

    assert response.status_code == 201
