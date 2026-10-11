"""HC-214: the node verifies Governance-signed synchronization authorizations itself."""

import json
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from adapters.outbound.ed25519_authorization_reader import (
    Ed25519AuthorizationReader,
    PublicKeyError,
)
from application.authorization_verifier import SignedDecisionVerifier
from domain.patient_history import (
    Authorization,
    AuthorizationBasis,
    HistoryQuery,
    Requester,
    ScopeItem,
)
from tests.signed_authorizations import (
    ISSUED_AT,
    PURPOSE,
    GovernanceSigner,
    at,
    b64url,
    claims,
)

SIGNER = GovernanceSigner()
READER = Ed25519AuthorizationReader(SIGNER.private_key.public_key())


def query(token: str | None = None, **changes) -> HistoryQuery:
    fields = {
        "query_id": "0b9f6c2e-3d41-4a8e-9f57-1c2d3e4f5a6b",
        "patient_ref": "pat-a",
        "scope": frozenset({ScopeItem.MEDICATIONS}),
        "purpose": PURPOSE,
        "requested_by": Requester("org-hospital-a", "clin-x"),
        "authorization": Authorization(
            AuthorizationBasis.SYNCHRONIZATION_DECISION,
            "dec-sync-001",
            ISSUED_AT + timedelta(days=13),
        ),
        "signed_authorization": SIGNER.sign() if token is None else token,
    }
    return HistoryQuery(**(fields | changes))


class Others:
    """The grant verifier, which a signed decision never reaches."""

    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.asked = []

    def allows(self, query, at) -> bool:
        self.asked.append(query)
        return self.answer


def verifier(others: Others | None = None) -> SignedDecisionVerifier:
    return SignedDecisionVerifier(
        READER, "org-governance", "org-hospital-b", others or Others(False)
    )


# Adapter: the signature and the format


def test_reads_what_the_governance_node_attested():
    attested = READER.read(SIGNER.sign())

    assert attested.decision_ref == "dec-sync-001"
    assert attested.audience_refs == {"org-hospital-b"}
    assert attested.scope == {ScopeItem.MEDICATIONS}
    assert (attested.issued_at, attested.expires_at) == (at(0), at(5))


def test_another_key_reads_nothing():
    assert READER.read(GovernanceSigner().sign()) is None


def test_a_changed_claim_reads_nothing():
    header, _, signature = SIGNER.sign().split(".")
    widened = b64url(json.dumps(claims(scope=["encounters", "medications"])).encode())

    assert READER.read(f"{header}.{widened}.{signature}") is None


@pytest.mark.parametrize(
    "header",
    [
        {"alg": "none", "typ": "governance-authorization+jwt"},
        {"alg": "HS256", "typ": "governance-authorization+jwt"},
        {"alg": "EdDSA", "kid": "another-key", "typ": "governance-authorization+jwt"},
        {"alg": "EdDSA", "typ": "JWT"},
        {"alg": "EdDSA", "typ": "governance-authorization+jwt", "crit": ["exp"]},
    ],
)
def test_an_unexpected_header_reads_nothing(header):
    header = {"kid": SIGNER.key_id} | header

    assert READER.read(SIGNER.sign(header=header)) is None


@pytest.mark.parametrize(
    "payload",
    [
        {k: v for k, v in claims().items() if k != "aud"},
        claims(extra="value"),
        claims(basis="patient_access_grant"),
        claims(aud=[]),
        claims(aud="org-hospital-b"),
        claims(scope=["prescriptions"]),
        claims(scope=[]),
        claims(purpose=""),
        claims(patient_ref="Leïla Ben Salah"),
        claims(exp="soon"),
        claims(iat=True),
        claims(exp=10**20),
        ["not", "an", "object"],
    ],
)
def test_claims_outside_the_contract_read_nothing(payload):
    assert READER.read(SIGNER.sign(payload)) is None


@pytest.mark.parametrize(
    "token", ["", "a.b", "a.b.c.d", "!!.!!.!!", "x" * 5000, "é.é.é"]
)
def test_malformed_tokens_read_nothing(token):
    assert READER.read(token) is None


def test_loads_a_public_key(tmp_path):
    path = tmp_path / "governance.pub.pem"
    path.write_bytes(SIGNER.public_key_pem())

    assert Ed25519AuthorizationReader.load(path).key_id == SIGNER.key_id


def test_refuses_a_missing_or_non_ed25519_public_key(tmp_path):
    with pytest.raises(PublicKeyError):
        Ed25519AuthorizationReader.load(tmp_path / "missing.pem")
    path = tmp_path / "ec.pub.pem"
    path.write_bytes(
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    with pytest.raises(PublicKeyError, match="not an Ed25519"):
        Ed25519AuthorizationReader.load(path)


# Domain and application: does it cover this query, here and now?


def test_a_covering_signed_authorization_allows_the_query():
    assert verifier().allows(query(), at(1))


def test_a_narrower_query_is_allowed():
    token = SIGNER.sign(claims(scope=["lab_reports", "medications"]))

    assert verifier().allows(query(token), at(1))


@pytest.mark.parametrize(
    "changes",
    [
        {"patient_ref": "pat-b"},
        {"purpose": "Étude interne"},
        {"scope": frozenset({ScopeItem.MEDICATIONS, ScopeItem.ENCOUNTERS})},
        {"requested_by": Requester("org-private-practice", "clin-x")},
        {"requested_by": Requester("org-hospital-a", "clin-y")},
        {
            "authorization": Authorization(
                AuthorizationBasis.SYNCHRONIZATION_DECISION,
                "dec-sync-002",
                ISSUED_AT + timedelta(days=13),
            )
        },
    ],
)
def test_any_difference_from_the_attested_exchange_is_denied(changes):
    assert not verifier().allows(query(**changes), at(1))


@pytest.mark.parametrize(
    "payload",
    [claims(aud=["org-hospital-a"]), claims(iss="org-platform")],
)
def test_another_audience_or_issuer_is_denied(payload):
    assert not verifier().allows(query(SIGNER.sign(payload)), at(1))


@pytest.mark.parametrize("minutes", [-2, 5, 60])
def test_denied_before_issue_and_from_expiry(minutes):
    assert not verifier().allows(query(), at(minutes))


def test_a_little_clock_skew_is_tolerated_before_issue():
    assert verifier().allows(query(), ISSUED_AT - timedelta(seconds=30))


def test_a_synchronization_decision_without_a_signed_authorization_is_denied():
    others = Others(True)

    assert not verifier(others).allows(query(signed_authorization=None), at(1))
    assert others.asked == []


def test_a_patient_access_grant_is_left_to_the_grant_store():
    others = Others(True)
    grant_query = query(
        authorization=Authorization(
            AuthorizationBasis.PATIENT_ACCESS_GRANT,
            "grant-a-drx",
            ISSUED_AT + timedelta(days=13),
        ),
    )

    assert verifier(others).allows(grant_query, at(1))
    assert others.asked == [grant_query]
