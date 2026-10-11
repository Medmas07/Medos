from collections.abc import Callable
from typing import Protocol

from domain.federation_authorization import AttestedAuthorization, attest
from domain.synchronization import AuthorizationCheck, ExchangeAsk


class AuthorizationSigner(Protocol):
    """Signs what the Governance Node attests (HC-214, ADR-0015).

    The token format and key belong to the adapter; Hospital Nodes verify the
    signature with the Authority's public key, distributed to them out of band."""

    algorithm: str  # reported by /health, for example "ed25519"

    def sign(self, attested: AttestedAuthorization) -> str: ...


def signed_authorization(
    check: AuthorizationCheck,
    ask: ExchangeAsk,
    signer: AuthorizationSigner | None,
    issuer_ref: str,
    new_token_id: Callable[[], str],
) -> str | None:
    """The signed authorization for an authorized check, or None: denied, or this
    Node does not sign (signing off)."""
    if signer is None or not check.authorized:
        return None
    return signer.sign(attest(check, ask, issuer_ref, new_token_id()))
