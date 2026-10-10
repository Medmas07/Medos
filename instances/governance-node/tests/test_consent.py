"""Consent evaluated against the Hospital Node holding the grant (HC-136): the rules."""

from dataclasses import replace
from datetime import timedelta

import pytest

from domain.synchronization import (
    AuthorizationCheck,
    CheckState,
    Consent,
    ConsentBasis,
    DenialReason,
    checks,
    reverify_consent,
)
from tests.conftest import DEMO_NOW
from tests.test_synchronization import CONTEXT, GRANT_A, SYNC_001

AUTHORIZED = AuthorizationCheck(
    "dec-sync-001",
    None,
    DEMO_NOW,
    target_organization_refs=("org-hospital-b",),
    scope=SYNC_001.scope,
    purpose=SYNC_001.purpose,
    valid_until=DEMO_NOW + timedelta(days=13),
)


def test_an_unreachable_holder_fails_the_consent_check():
    context = replace(
        CONTEXT,
        grant=None,
        grant_unavailable="the Hospital Node of org-hospital-b could not be reached.",
    )

    consent = checks(SYNC_001, context)[1]

    assert (consent.state, consent.detail) == (
        CheckState.FAIL,
        "Grant grant-a-drx could not be verified: the Hospital Node of "
        "org-hospital-b could not be reached.",
    )


def test_a_grant_still_active_keeps_the_authorization():
    assert reverify_consent(AUTHORIZED, SYNC_001, GRANT_A, DEMO_NOW) == AUTHORIZED


@pytest.mark.parametrize(
    "grant",
    [
        replace(GRANT_A, revoked=True),
        None,  # unknown to the holder now
        replace(GRANT_A, expires_at=DEMO_NOW),
    ],
)
def test_a_withdrawn_grant_revokes_the_authorization(grant):
    result = reverify_consent(AUTHORIZED, SYNC_001, grant, DEMO_NOW)

    assert (result.reason, result.target_organization_refs, result.scope) == (
        DenialReason.REVOKED,
        (),
        frozenset(),
    )
    assert result.valid_until == AUTHORIZED.valid_until


def test_only_an_authorization_relying_on_a_patient_grant_is_reverified():
    signed = replace(SYNC_001, consent=Consent(ConsentBasis.SIGNED_CONSENT_FORM))
    denied = replace(AUTHORIZED, reason=DenialReason.EXPIRED)

    assert reverify_consent(AUTHORIZED, signed, None, DEMO_NOW) == AUTHORIZED
    assert reverify_consent(denied, SYNC_001, None, DEMO_NOW) == denied
