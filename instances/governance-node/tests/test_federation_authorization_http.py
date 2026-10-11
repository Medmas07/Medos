"""HC-214: the Governance Node signs authorized synchronization checks."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from adapters.outbound.ed25519_authorization_signer import (
    Ed25519AuthorizationSigner,
    SigningKeyError,
)
from adapters.outbound.in_memory_hospital_applications import SeedError
from main import create_app, signer_from_env
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_federation_authorization import verify
from tests.test_synchronization_http import (
    CHECK,
    CHECK_OP,
    Clock,
    ask,
    check,
    decide,
    example,
)

SIGNER = Ed25519AuthorizationSigner.generate()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(clock) -> TestClient:
    return TestClient(create_app(demo_data=DEMO_DATA, clock=clock, signer=SIGNER))


def test_health_reports_signing(client):
    assert client.get("/health").json()["federation_signing"] == "ed25519"
    assert TestClient(create_app()).get("/health").json()["federation_signing"] == (
        "off"
    )


def test_an_authorized_check_carries_a_signed_authorization(client, clock):
    decide(client, "sync-001")
    clock.now = DEMO_NOW + timedelta(minutes=30)

    body = check(ask(client, "dec-sync-001"), CHECK, CHECK_OP, 200)

    unsigned = example(CHECK, CHECK_OP, 200, "authorized")
    assert {**body, "signed_authorization": None} == unsigned
    _, claims = verify(SIGNER, body["signed_authorization"])
    assert (claims["iss"], claims["sub"], claims["aud"]) == (
        "org-governance",
        "dec-sync-001",
        ["org-hospital-b"],
    )
    assert claims["scope"] == ["medications"]
    assert claims["exp"] - claims["iat"] == 300


def test_each_check_gets_its_own_token(client):
    decide(client, "sync-001")

    first = ask(client, "dec-sync-001").json()["signed_authorization"]
    second = ask(client, "dec-sync-001").json()["signed_authorization"]

    assert verify(SIGNER, first)[1]["jti"] != verify(SIGNER, second)[1]["jti"]


@pytest.mark.parametrize(
    "decision_ref, changes",
    [("dec-sync-002", {}), ("dec-sync-001", {"patient_ref": "pat-b"})],
)
def test_a_denied_check_is_never_signed(client, decision_ref, changes):
    decide(client, "sync-001")

    body = check(ask(client, decision_ref, **changes), CHECK, CHECK_OP, 200)

    assert (body["outcome"], body["signed_authorization"]) == ("denied", None)


def test_an_unsigned_node_answers_null(clock):
    client = TestClient(create_app(demo_data=DEMO_DATA, clock=clock))
    decide(client, "sync-001")

    body = check(ask(client, "dec-sync-001"), CHECK, CHECK_OP, 200)

    assert (body["outcome"], body["signed_authorization"]) == ("authorized", None)


def test_the_signed_example_matches_the_contract_shape():
    signed = example(CHECK, CHECK_OP, 200, "authorizedSigned")
    header, claims, signature = signed["signed_authorization"].split(".")

    assert header and claims and signature


# Startup: GOVERNANCE_FEDERATION_SIGNING


def test_signing_is_off_by_default(monkeypatch):
    monkeypatch.delenv("GOVERNANCE_FEDERATION_SIGNING", raising=False)

    assert signer_from_env() is None


def test_signing_loads_the_configured_key(monkeypatch, tmp_path):
    path = tmp_path / "signing-key.pem"
    path.write_bytes(SIGNER.private_key_pem())
    monkeypatch.setenv("GOVERNANCE_FEDERATION_SIGNING", "ed25519")
    monkeypatch.setenv("GOVERNANCE_SIGNING_KEY", str(path))

    assert signer_from_env().key_id == SIGNER.key_id


def test_signing_without_a_key_stops_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("GOVERNANCE_FEDERATION_SIGNING", "ed25519")
    monkeypatch.setenv("GOVERNANCE_SIGNING_KEY", str(tmp_path / "missing.pem"))

    with pytest.raises(SigningKeyError):
        signer_from_env()


def test_an_unknown_signing_mode_stops_startup(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_FEDERATION_SIGNING", "hmac")

    with pytest.raises(SeedError):
        signer_from_env()
