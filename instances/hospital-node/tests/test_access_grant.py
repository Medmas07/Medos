from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from domain.access_grant import AccessGrant, GrantStatus, InvalidAccessGrant
from domain.patient_history import (
    Authorization,
    AuthorizationBasis,
    HistoryQuery,
    Requester,
    ScopeItem,
)
from tests.conftest import DEMO_NOW

GRANT = AccessGrant(
    grant_ref="grant-1",
    patient_ref="pat-1",
    grantee_ref="clin-1",
    scope=frozenset({ScopeItem.MEDICATIONS, ScopeItem.ENCOUNTERS}),
    purpose="Consultation",
    granted_at=DEMO_NOW - timedelta(days=1),
    expires_at=DEMO_NOW + timedelta(days=1),
)


def query(**changes) -> HistoryQuery:
    fields = {
        "query_id": "0b9f6c2e-3d41-4a8e-9f57-1c2d3e4f5a6b",
        "patient_ref": "pat-1",
        "scope": frozenset({ScopeItem.MEDICATIONS}),
        "purpose": "Consultation",
        "requested_by": Requester("org-1", "clin-1"),
        "authorization": Authorization(
            AuthorizationBasis.PATIENT_ACCESS_GRANT, "grant-1", DEMO_NOW
        ),
    }
    return HistoryQuery(**(fields | changes))


def test_is_active_until_it_expires():
    assert GRANT.status(DEMO_NOW) is GrantStatus.ACTIVE
    assert GRANT.status(GRANT.expires_at) is GrantStatus.EXPIRED


def test_a_grant_recorded_as_no_longer_in_force_is_expired():
    assert replace(GRANT, in_force=False).status(DEMO_NOW) is GrantStatus.EXPIRED


def test_revocation_is_recorded_and_denies_from_then_on():
    revoked = GRANT.revoked(DEMO_NOW)

    assert revoked.revoked_at == DEMO_NOW
    assert revoked.status(DEMO_NOW) is GrantStatus.REVOKED
    assert GRANT.allows(query(), DEMO_NOW)
    assert not revoked.allows(query(), DEMO_NOW)


def test_revoking_twice_keeps_the_first_revocation():
    first = GRANT.revoked(DEMO_NOW)

    assert first.revoked(DEMO_NOW + timedelta(hours=1)) == first


def test_an_expired_grant_can_still_be_revoked():
    later = GRANT.expires_at + timedelta(days=1)

    assert GRANT.revoked(later).status(later) is GrantStatus.REVOKED


@pytest.mark.parametrize(
    "changes",
    [
        {"requested_by": Requester("org-1", "clin-2")},
        {"patient_ref": "pat-2"},
        {"purpose": "Recherche"},
        {"scope": frozenset(ScopeItem)},
    ],
    ids=["other-actor", "other-patient", "other-purpose", "wider-scope"],
)
def test_allows_only_its_grantee_patient_purpose_and_scope(changes):
    assert not GRANT.allows(query(**changes), DEMO_NOW)


@pytest.mark.parametrize(
    "changes",
    [
        {"grantee_ref": "Dr Karim"},
        {"scope": frozenset()},
        {"purpose": ""},
        {"purpose": "x" * 201},
        {"expires_at": GRANT.granted_at},
        {"granted_at": datetime(2026, 10, 9)},
    ],
    ids=[
        "non-opaque-grantee",
        "empty-scope",
        "empty-purpose",
        "long-purpose",
        "expires-when-granted",
        "no-offset",
    ],
)
def test_an_invalid_grant_is_rejected(changes):
    with pytest.raises(InvalidAccessGrant):
        replace(GRANT, **changes)
