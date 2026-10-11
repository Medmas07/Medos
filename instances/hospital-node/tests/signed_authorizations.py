"""Test double of the Governance Node's signer (HC-214): signs what a test asks, with a
key the test holds, in the format of contracts/federation/sync-authorization-check.v1.yaml."""

import base64
import json
from datetime import datetime, timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from adapters.outbound.ed25519_authorization_reader import key_id
from tests.conftest import DEMO_NOW

# Demo step 20: the decision approving sync-001, Hospital A asking Hospital B.
PURPOSE = "Continuité des soins : consultation de cardiologie"
ISSUED_AT = DEMO_NOW


def claims(**changes) -> dict:
    return {
        "iss": "org-governance",
        "sub": "dec-sync-001",
        "aud": ["org-hospital-b"],
        "jti": "4f6c1d0e-8a5b-4c3e-9b1a-2d7e6f5a4b3c",
        "iat": int(ISSUED_AT.timestamp()),
        "exp": int((ISSUED_AT + timedelta(minutes=5)).timestamp()),
        "basis": "synchronization_decision",
        "requester_organization_ref": "org-hospital-a",
        "actor_ref": "clin-x",
        "patient_ref": "pat-a",
        "scope": ["medications"],
        "purpose": PURPOSE,
    } | changes


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class GovernanceSigner:
    def __init__(self) -> None:
        self.private_key = Ed25519PrivateKey.generate()
        self.key_id = key_id(self.private_key.public_key())

    def public_key_pem(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def sign(self, payload: dict | None = None, header: dict | None = None) -> str:
        header = header or {
            "alg": "EdDSA",
            "kid": self.key_id,
            "typ": "governance-authorization+jwt",
        }
        signing_input = (
            b64url(json.dumps(header).encode())
            + "."
            + b64url(json.dumps(claims() if payload is None else payload).encode())
        )
        signature = self.private_key.sign(signing_input.encode("ascii"))
        return f"{signing_input}.{b64url(signature)}"


def at(minutes: int) -> datetime:
    return ISSUED_AT + timedelta(minutes=minutes)
