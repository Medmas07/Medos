"""Signed federation authorization (HC-214, ADR-0015).

When the Governance Node authorizes an exchange under a synchronization decision, it
also states what it authorized in a form the target Hospital Node can verify on its
own: the Authority, the decision, the target organizations, and the exact exchange
asked (requester, actor, patient, scope, purpose), for a short time. The signature is
an adapter's concern; these are the rules of what is attested.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.synchronization import AuthorizationCheck, ExchangeAsk, ScopeItem

# Short, so that a decision expiring or a patient grant being withdrawn stops the
# exchange soon after, without the Hospital Node asking the Governance Node again.
LIFETIME = timedelta(minutes=5)


class NotAuthorized(ValueError):
    pass


@dataclass(frozen=True)
class AttestedAuthorization:
    token_id: str
    issuer_ref: str  # the Governance / Ethics Authority's organization
    decision_ref: str
    audience_refs: tuple[str, ...]  # the organizations whose nodes may answer
    requester_organization_ref: str
    actor_ref: str
    patient_ref: str
    scope: frozenset[ScopeItem]
    purpose: str
    issued_at: datetime
    expires_at: datetime


def attest(
    check: AuthorizationCheck, ask: ExchangeAsk, issuer_ref: str, token_id: str
) -> AttestedAuthorization:
    """What an authorized check attests: the exchange asked, never more than approved,
    until the decision's end or LIFETIME after the check, whichever comes first."""
    if not check.authorized or check.valid_until is None:
        raise NotAuthorized(f"{check.decision_ref} does not authorize this exchange")
    return AttestedAuthorization(
        token_id=token_id,
        issuer_ref=issuer_ref,
        decision_ref=check.decision_ref,
        audience_refs=check.target_organization_refs,
        requester_organization_ref=ask.requester_organization_ref,
        actor_ref=ask.actor_ref,
        patient_ref=ask.patient_ref,
        # The check already holds ask.scope <= approved scope: only what was asked.
        scope=ask.scope,
        purpose=ask.purpose,
        issued_at=check.checked_at,
        expires_at=min(check.valid_until, check.checked_at + LIFETIME),
    )
