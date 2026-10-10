"""Consent policy evaluation over HTTP (HC-136), against the contracts.

The Governance Node asks the Hospital Node holding a patient grant: here a test double
stands for Hospital B, which can revoke the grant or stop answering. The answers are
the examples of sync-authorization-check.v1.yaml.
"""

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from application.synchronization import GrantsUnavailable
from main import create_app
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_synchronization import GRANT_A
from tests.test_synchronization_http import (
    CHECK,
    CHECK_OP,
    DETAIL,
    SYNC,
    Clock,
    ask,
    check,
    decide,
    example,
)


class HospitalB:
    """Test double at the PatientGrantDirectory port: Hospital B's grants."""

    mode = "http"

    def __init__(self) -> None:
        self.grants = {GRANT_A.grant_ref: GRANT_A}
        self.running = True

    def grant(self, holder_organization_ref, patient_ref, grant_ref):
        if not self.running:
            raise GrantsUnavailable(
                f"the Hospital Node of {holder_organization_ref} could not be reached."
            )
        assert holder_organization_ref == "org-hospital-b"
        grant = self.grants.get(grant_ref)
        return grant if grant and grant.patient_ref == patient_ref else None

    def revoke(self, grant_ref: str) -> None:
        self.grants[grant_ref] = replace(self.grants[grant_ref], revoked=True)


@pytest.fixture
def hospital_b() -> HospitalB:
    return HospitalB()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(hospital_b, clock) -> TestClient:
    return TestClient(create_app(demo_data=DEMO_DATA, clock=clock, grants=hospital_b))


def approve_sync_001(client, clock) -> None:
    check(
        decide(client, "sync-001"),
        SYNC,
        SYNC["paths"]["/v1/synchronization-requests/{request_ref}/decision"]["post"],
        201,
    )
    clock.now = DEMO_NOW + timedelta(minutes=30)


def test_health_reports_the_grant_source(client):
    assert client.get("/health").json()["grants"] == "http"


def test_a_grant_revoked_at_hospital_b_stops_the_synchronization(
    client, clock, hospital_b
):
    approve_sync_001(client, clock)
    assert check(ask(client, "dec-sync-001"), CHECK, CHECK_OP, 200) == example(
        CHECK, CHECK_OP, 200, "authorized"
    )

    hospital_b.revoke("grant-a-drx")

    assert check(ask(client, "dec-sync-001"), CHECK, CHECK_OP, 200) == example(
        CHECK, CHECK_OP, 200, "grantRevoked"
    )
    [event] = client.get(
        "/v1/audit/events?subject_ref=dec-sync-001&action=authorization_checked&limit=1"
    ).json()["events"]
    assert (event["outcome"], event["reason"]) == ("denied", "revoked")


def test_an_unreachable_hospital_b_authorizes_nothing(client, clock, hospital_b):
    approve_sync_001(client, clock)
    hospital_b.running = False

    assert check(ask(client, "dec-sync-001"), CHECK, CHECK_OP, 503) == example(
        CHECK, CHECK_OP, 503, "consentUnavailable"
    )
    [event] = client.get(
        "/v1/audit/events?subject_ref=dec-sync-001&action=authorization_checked&limit=1"
    ).json()["events"]
    assert (event["outcome"], event["reason"]) == ("denied", "consent_unavailable")


def test_the_review_shows_a_consent_that_cannot_be_verified(client, hospital_b):
    hospital_b.running = False

    body = check(client.get("/v1/synchronization-requests/sync-001"), SYNC, DETAIL, 200)

    assert body["checks"][1] == {
        "check": "consent",
        "state": "fail",
        "detail": "Grant grant-a-drx could not be verified: the Hospital Node of "
        "org-hospital-b could not be reached.",
    }
    refused = decide(client, "sync-001")
    assert refused.status_code == 422


def test_a_manual_consent_basis_is_not_asked_of_any_node(client, clock, hospital_b):
    hospital_b.running = False
    purpose = "Continuité des soins : formulaire de consentement signé"
    submitted = client.post(
        "/v1/synchronization-requests",
        json={
            "requester_organization_ref": "org-hospital-a",
            "submitted_by_ref": "clin-x",
            "target_organization_ref": "org-hospital-b",
            "patient_ref": "pat-a",
            "purpose": purpose,
            "scope": ["medications"],
            "duration_days": 5,
            "consent": {"basis": "signed_consent_form", "access_grant_ref": None},
        },
    ).json()
    ref = submitted["request_ref"]
    approved = decide(client, ref, approved_days=5, manual_checks_confirmed=True)
    assert approved.status_code == 201, approved.text
    clock.now = DEMO_NOW + timedelta(minutes=30)

    body = check(ask(client, f"dec-{ref}", purpose=purpose), CHECK, CHECK_OP, 200)
    assert body["outcome"] == "authorized"
