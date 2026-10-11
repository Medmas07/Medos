import base64
import json
from datetime import timedelta

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from adapters.outbound.ed25519_authorization_signer import (
    Ed25519AuthorizationSigner,
    SigningKeyError,
)
from application.federation_authorization import signed_authorization
from domain.federation_authorization import LIFETIME, NotAuthorized, attest
from domain.synchronization import (
    AuthorizationCheck,
    DenialReason,
    ExchangeAsk,
    ScopeItem,
)
from tests.conftest import DEMO_NOW

ASK = ExchangeAsk(
    "org-hospital-a",
    "clin-x",
    "pat-a",
    frozenset({ScopeItem.MEDICATIONS}),
    "Continuité des soins : consultation de cardiologie",
)
AUTHORIZED = AuthorizationCheck(
    "dec-sync-001",
    None,
    DEMO_NOW,
    target_organization_refs=("org-hospital-b",),
    scope=frozenset({ScopeItem.MEDICATIONS, ScopeItem.LAB_REPORTS}),
    purpose=ASK.purpose,
    valid_until=DEMO_NOW + timedelta(days=13),
)
DENIED = AuthorizationCheck(
    "dec-sync-001", DenialReason.EXPIRED, DEMO_NOW, valid_until=DEMO_NOW
)


def decode(part: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def verify(signer: Ed25519AuthorizationSigner, token: str) -> tuple[dict, dict]:
    """What a Hospital Node does with the public key alone."""
    header, claims, signature = token.split(".")
    public_key = load_pem_public_key(signer.public_key_pem())
    public_key.verify(
        base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)),
        f"{header}.{claims}".encode("ascii"),
    )
    return decode(header), decode(claims)


# Domain: what an authorized check attests


def test_attests_the_exchange_asked_for_the_targets_for_five_minutes():
    attested = attest(AUTHORIZED, ASK, "org-governance", "tok-1")

    assert attested.issuer_ref == "org-governance"
    assert attested.decision_ref == "dec-sync-001"
    assert attested.audience_refs == ("org-hospital-b",)
    assert (attested.requester_organization_ref, attested.actor_ref) == (
        "org-hospital-a",
        "clin-x",
    )
    assert attested.patient_ref == "pat-a"
    assert attested.purpose == ASK.purpose
    assert (attested.issued_at, attested.expires_at) == (
        DEMO_NOW,
        DEMO_NOW + LIFETIME,
    )


def test_attests_only_the_scope_asked_not_the_wider_approval():
    assert attest(AUTHORIZED, ASK, "org-governance", "tok-1").scope == {
        ScopeItem.MEDICATIONS
    }


def test_never_outlives_the_decision():
    ending = AuthorizationCheck(
        **{**AUTHORIZED.__dict__, "valid_until": DEMO_NOW + timedelta(minutes=1)}
    )

    assert attest(ending, ASK, "org-governance", "tok-1").expires_at == (
        DEMO_NOW + timedelta(minutes=1)
    )


def test_a_denied_check_attests_nothing():
    with pytest.raises(NotAuthorized):
        attest(DENIED, ASK, "org-governance", "tok-1")


# Application: signing only what is authorized, and only when this Node signs


def test_no_signed_authorization_when_denied_or_not_signing():
    signer = Ed25519AuthorizationSigner.generate()

    assert signed_authorization(DENIED, ASK, signer, "org-governance", str) is None
    assert signed_authorization(AUTHORIZED, ASK, None, "org-governance", str) is None


# Adapter: Ed25519 compact JWS


def test_signs_a_compact_jws_with_the_contract_claims():
    signer = Ed25519AuthorizationSigner.generate()

    token = signed_authorization(
        AUTHORIZED, ASK, signer, "org-governance", lambda: "tok-1"
    )
    header, claims = verify(signer, token)

    assert header == {
        "alg": "EdDSA",
        "kid": signer.key_id,
        "typ": "governance-authorization+jwt",
    }
    assert claims == {
        "iss": "org-governance",
        "sub": "dec-sync-001",
        "aud": ["org-hospital-b"],
        "jti": "tok-1",
        "iat": int(DEMO_NOW.timestamp()),
        "exp": int((DEMO_NOW + LIFETIME).timestamp()),
        "basis": "synchronization_decision",
        "requester_organization_ref": "org-hospital-a",
        "actor_ref": "clin-x",
        "patient_ref": "pat-a",
        "scope": ["medications"],
        "purpose": ASK.purpose,
    }


def test_a_changed_claim_breaks_the_signature():
    signer = Ed25519AuthorizationSigner.generate()
    header, claims, signature = signer.sign(
        attest(AUTHORIZED, ASK, "org-governance", "tok-1")
    ).split(".")
    widened = decode(claims) | {"scope": ["encounters", "medications"]}
    forged = base64.urlsafe_b64encode(json.dumps(widened).encode()).rstrip(b"=")

    with pytest.raises(InvalidSignature):
        verify(signer, f"{header}.{forged.decode()}.{signature}")


def test_another_key_does_not_verify():
    token = Ed25519AuthorizationSigner.generate().sign(
        attest(AUTHORIZED, ASK, "org-governance", "tok-1")
    )

    with pytest.raises(InvalidSignature):
        verify(Ed25519AuthorizationSigner.generate(), token)


def test_the_key_id_is_the_rfc_7638_thumbprint():
    # RFC 8037, appendix A.3: the thumbprint of its example Ed25519 key.
    from adapters.outbound.ed25519_authorization_signer import key_id

    raw = base64.urlsafe_b64decode("11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo=")

    assert key_id(raw) == "kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k"


def test_loads_the_key_it_wrote(tmp_path):
    signer = Ed25519AuthorizationSigner.generate()
    path = tmp_path / "signing-key.pem"
    path.write_bytes(signer.private_key_pem())

    assert Ed25519AuthorizationSigner.load(path).key_id == signer.key_id


@pytest.mark.parametrize("content", [None, b"not a key"])
def test_refuses_a_missing_or_invalid_key(tmp_path, content):
    path = tmp_path / "signing-key.pem"
    if content is not None:
        path.write_bytes(content)

    with pytest.raises(SigningKeyError):
        Ed25519AuthorizationSigner.load(path)


def test_refuses_a_key_that_is_not_ed25519(tmp_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    path = tmp_path / "signing-key.pem"
    path.write_bytes(
        ec.generate_private_key(ec.SECP256R1()).private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

    with pytest.raises(SigningKeyError, match="not an Ed25519"):
        Ed25519AuthorizationSigner.load(path)
