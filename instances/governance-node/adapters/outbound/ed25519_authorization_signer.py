"""AuthorizationSigner with Ed25519 (HC-214, ADR-0015).

A signed authorization is a compact JWS (RFC 7515) with alg EdDSA (RFC 8037), whose
header and claims are described in contracts/federation/sync-authorization-check.v1.yaml.
The private key is a PKCS#8 PEM file created by auth/create_signing_key.py, never
committed; the matching public key is the one each Hospital Node is configured to trust,
named in the header by its RFC 7638 thumbprint.
"""

import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from domain.federation_authorization import AttestedAuthorization

TOKEN_TYPE = "governance-authorization+jwt"
BASIS = "synchronization_decision"


class SigningKeyError(RuntimeError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _json(value: dict) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def key_id(public_key_raw: bytes) -> str:
    """RFC 7638 JWK thumbprint of an Ed25519 public key."""
    jwk = {"crv": "Ed25519", "kty": "OKP", "x": _b64url(public_key_raw)}
    return _b64url(hashlib.sha256(_json(jwk)).digest())


class Ed25519AuthorizationSigner:
    algorithm = "ed25519"

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private_key = private_key
        self.key_id = key_id(self._public_raw())

    @classmethod
    def generate(cls) -> "Ed25519AuthorizationSigner":
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def load(cls, path: Path) -> "Ed25519AuthorizationSigner":
        """Refuses to start on a missing, unreadable, or non-Ed25519 key."""
        try:
            private_key = serialization.load_pem_private_key(
                path.read_bytes(), password=None
            )
        except (OSError, ValueError, TypeError) as error:
            raise SigningKeyError(f"Cannot read signing key {path}: {error}") from error
        if not isinstance(private_key, Ed25519PrivateKey):
            raise SigningKeyError(f"{path} is not an Ed25519 private key")
        return cls(private_key)

    def private_key_pem(self) -> bytes:
        return self._private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    def public_key_pem(self) -> bytes:
        return self._private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def sign(self, attested: AttestedAuthorization) -> str:
        header = {"alg": "EdDSA", "kid": self.key_id, "typ": TOKEN_TYPE}
        claims = {
            "iss": attested.issuer_ref,
            "sub": attested.decision_ref,
            "aud": list(attested.audience_refs),
            "jti": attested.token_id,
            "iat": int(attested.issued_at.timestamp()),
            "exp": int(attested.expires_at.timestamp()),
            "basis": BASIS,
            "requester_organization_ref": attested.requester_organization_ref,
            "actor_ref": attested.actor_ref,
            "patient_ref": attested.patient_ref,
            "scope": sorted(item.value for item in attested.scope),
            "purpose": attested.purpose,
        }
        signing_input = f"{_b64url(_json(header))}.{_b64url(_json(claims))}"
        signature = self._private_key.sign(signing_input.encode("ascii"))
        return f"{signing_input}.{_b64url(signature)}"

    def _public_raw(self) -> bytes:
        return self._private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
