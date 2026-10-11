"""SignedAuthorizationReader with Ed25519 (HC-214, ADR-0015).

Reads the compact JWS of contracts/federation/sync-authorization-check.v1.yaml: the
protected header must be exactly alg EdDSA, the trusted key's RFC 7638 thumbprint as
kid, and typ governance-authorization+jwt; the claims must be exactly those of the
contract. The signature is verified with the Governance Node's public key, a PEM file
this hospital configures (`governance_public_key`), distributed to it out of band.
Anything else reads as None, so the query is denied.
"""

import base64
import binascii
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from domain.node_identity import is_opaque_ref
from domain.patient_history import ScopeItem
from domain.signed_authorization import SignedAuthorization

TOKEN_TYPE = "governance-authorization+jwt"
BASIS = "synchronization_decision"
MAX_LENGTH = 4096
CLAIMS = {
    "iss",
    "sub",
    "aud",
    "jti",
    "iat",
    "exp",
    "basis",
    "requester_organization_ref",
    "actor_ref",
    "patient_ref",
    "scope",
    "purpose",
}


class PublicKeyError(RuntimeError):
    pass


def _b64url_decode(part: str) -> bytes:
    if not part or "=" in part:
        raise ValueError("not unpadded base64url")
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def key_id(public_key: Ed25519PublicKey) -> str:
    """RFC 7638 JWK thumbprint of an Ed25519 public key."""
    raw = public_key.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    jwk = {"crv": "Ed25519", "kty": "OKP", "x": _b64url(raw)}
    canonical = json.dumps(jwk, separators=(",", ":"), sort_keys=True)
    return _b64url(hashlib.sha256(canonical.encode("utf-8")).digest())


def _ref(value: object) -> str:
    if not isinstance(value, str) or not is_opaque_ref(value):
        raise ValueError("not an opaque reference")
    return value


def _time(value: object) -> datetime:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("not a NumericDate")
    return datetime.fromtimestamp(value, UTC)


class Ed25519AuthorizationReader:
    def __init__(self, public_key: Ed25519PublicKey) -> None:
        self._public_key = public_key
        self.key_id = key_id(public_key)

    @classmethod
    def load(cls, path: Path) -> "Ed25519AuthorizationReader":
        """Refuses to start on a missing, unreadable, or non-Ed25519 public key."""
        try:
            public_key = serialization.load_pem_public_key(path.read_bytes())
        except (OSError, ValueError, TypeError) as error:
            raise PublicKeyError(
                f"Cannot read Governance public key {path}: {error}"
            ) from error
        if not isinstance(public_key, Ed25519PublicKey):
            raise PublicKeyError(f"{path} is not an Ed25519 public key")
        return cls(public_key)

    def read(self, token: str) -> SignedAuthorization | None:
        try:
            return self._read(token)
        except (
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
            OSError,  # a timestamp out of the platform's range
            binascii.Error,
            InvalidSignature,
        ):
            return None

    def _read(self, token: str) -> SignedAuthorization:
        if len(token) > MAX_LENGTH:
            raise ValueError("too long")
        header_part, claims_part, signature_part = token.split(".")
        header = json.loads(_b64url_decode(header_part))
        if header != {"alg": "EdDSA", "kid": self.key_id, "typ": TOKEN_TYPE}:
            raise ValueError("unexpected header")
        # Verified before the claims are interpreted.
        self._public_key.verify(
            _b64url_decode(signature_part),
            f"{header_part}.{claims_part}".encode("ascii"),
        )
        claims = json.loads(_b64url_decode(claims_part))
        if not isinstance(claims, dict) or set(claims) != CLAIMS:
            raise ValueError("unexpected claims")
        if claims["basis"] != BASIS:
            raise ValueError("unexpected basis")
        audience, scope, purpose = claims["aud"], claims["scope"], claims["purpose"]
        if not isinstance(audience, list) or not audience:
            raise ValueError("invalid audience")
        if not isinstance(scope, list) or not scope:
            raise ValueError("invalid scope")
        if not isinstance(purpose, str) or not purpose:
            raise ValueError("invalid purpose")
        if not isinstance(claims["jti"], str) or not claims["jti"]:
            raise ValueError("invalid jti")
        return SignedAuthorization(
            token_id=claims["jti"],
            issuer_ref=_ref(claims["iss"]),
            decision_ref=_ref(claims["sub"]),
            audience_refs=frozenset(_ref(ref) for ref in audience),
            requester_organization_ref=_ref(claims["requester_organization_ref"]),
            actor_ref=_ref(claims["actor_ref"]),
            patient_ref=_ref(claims["patient_ref"]),
            scope=frozenset(ScopeItem(item) for item in scope),
            purpose=purpose,
            issued_at=_time(claims["iat"]),
            expires_at=_time(claims["exp"]),
        )
