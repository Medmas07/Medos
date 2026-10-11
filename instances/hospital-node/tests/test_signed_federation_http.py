"""HC-214: Hospital B, configured with the Governance Node's public key, answers a query
under a synchronization decision only with a signed authorization that covers it."""

import json

import pytest
from fastapi.testclient import TestClient

from adapters.outbound.ed25519_authorization_reader import PublicKeyError
from infrastructure.config import ConfigError, load_config
from main import create_app
from tests.conftest import CONFIG_DIR
from tests.signed_authorizations import PURPOSE, GovernanceSigner, at, claims
from tests.test_federation_http import QUERY_OPERATION, schema

SIGNER = GovernanceSigner()
# Demo step 20's decision, recorded at runtime by the Governance Node: the MOCKED
# fixture decisions do not know it, so only its signed authorization can allow it.
SYNC_QUERY = {
    "query_id": "0b9f6c2e-3d41-4a8e-9f57-1c2d3e4f5a6b",
    "patient_ref": "pat-a",
    "scope": ["medications"],
    "purpose": PURPOSE,
    "requested_by": {"organization_ref": "org-hospital-a", "actor_ref": "clin-x"},
    "authorization": {
        "basis": "synchronization_decision",
        "ref": "dec-sync-001",
        "expires_at": "2026-10-23T10:00:00+01:00",
    },
}


def signed_config(tmp_path, public_key: bytes | None = None, **changes):
    key = tmp_path / "governance.pub.pem"
    key.write_bytes(public_key or SIGNER.public_key_pem())
    demo = json.loads((CONFIG_DIR / "hospital-b.demo.json").read_text("utf-8"))
    # Paths of the demo configuration are relative to config/.
    for field in demo:
        if field.startswith(("mock_", "storage_")):
            demo[field] = str((CONFIG_DIR / demo[field]).resolve())
    path = tmp_path / "hospital-b.signed.json"
    path.write_text(
        json.dumps(demo | {"governance_public_key": str(key)} | changes), "utf-8"
    )
    return load_config(path)


@pytest.fixture
def client(tmp_path) -> TestClient:
    return TestClient(create_app(signed_config(tmp_path), clock=lambda: at(1)))


def ask(client, **changes):
    return client.post("/v1/federation/queries", json=SYNC_QUERY | changes)


def test_health_reports_signed_decisions(client):
    assert client.get("/health").json()["synchronization_decisions"] == "signed"


def test_a_signed_authorization_discloses_the_attested_scope(client):
    response = ask(client, signed_authorization=SIGNER.sign())

    assert response.status_code == 200, response.text
    schema("NodeQueryResult").validate(response.json())
    assert [e["entry_ref"] for e in response.json()["entries"]] == [
        "med-b-leila-coagulix"
    ]


def test_the_contract_accepts_the_request():
    schema("NodeQueryRequest").validate(
        SYNC_QUERY | {"signed_authorization": SIGNER.sign()}
    )
    assert "signed_authorization" not in QUERY_OPERATION["requestBody"]["content"][
        "application/json"
    ]["schema"].get("required", [])


@pytest.mark.parametrize(
    "token",
    [
        None,
        GovernanceSigner().sign(),
        SIGNER.sign(claims(aud=["org-hospital-a"])),
        SIGNER.sign(claims(scope=["encounters"])),
        SIGNER.sign(claims(exp=int(at(1).timestamp()))),
    ],
)
def test_without_a_covering_signed_authorization_nothing_is_disclosed(client, token):
    changes = {} if token is None else {"signed_authorization": token}

    response = ask(client, **changes)

    assert response.status_code == 403
    assert response.json()["code"] == "authorization_denied"


def test_every_answer_is_audited(client):
    ask(client, signed_authorization=SIGNER.sign())
    ask(client)

    events = client.get("/v1/audit/events").json()["events"]
    assert sorted(e["outcome"] for e in events) == ["denied", "disclosed"]


def test_a_malformed_signed_authorization_is_invalid(client):
    response = ask(client, signed_authorization="not a token")

    assert response.status_code == 400
    assert "signed_authorization" in response.json()["detail"]


def test_patient_access_grants_still_come_from_the_grant_store(client):
    grant_query = SYNC_QUERY | {
        "purpose": "Consultation de cardiologie",
        "authorization": {
            "basis": "patient_access_grant",
            "ref": "grant-a-drx",
            "expires_at": "2026-10-24T09:00:00+01:00",
        },
    }

    assert client.post("/v1/federation/queries", json=grant_query).status_code == 200


def test_without_a_public_key_the_fixture_decisions_stand_in():
    config = load_config(CONFIG_DIR / "hospital-b.demo.json")
    client = TestClient(create_app(config, clock=lambda: at(1)))

    assert client.get("/health").json()["synchronization_decisions"] == "fixture"
    assert ask(client, signed_authorization=SIGNER.sign()).status_code == 403


def test_an_invalid_public_key_stops_startup(tmp_path):
    with pytest.raises(PublicKeyError):
        create_app(signed_config(tmp_path, public_key=b"not a key"))


def test_an_invalid_issuer_reference_is_refused(tmp_path):
    with pytest.raises(ConfigError):
        signed_config(tmp_path, governance_organization_ref="Governance Authority")
