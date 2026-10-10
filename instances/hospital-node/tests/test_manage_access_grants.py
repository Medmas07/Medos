from dataclasses import replace
from datetime import timedelta

import pytest

from adapters.outbound.in_memory_access_grant_store import InMemoryAccessGrantStore
from application.manage_access_grants import (
    GrantNotFound,
    grant_access,
    list_access_grants,
    revoke_access_grant,
)
from domain.access_grant import GrantStatus, InvalidAccessGrant
from domain.patient_history import ScopeItem
from tests.conftest import DEMO_NOW
from tests.test_access_grant import GRANT


def clock():
    return DEMO_NOW


def grant(store, expires_at=DEMO_NOW + timedelta(days=30)):
    return grant_access(
        "pat-1",
        "clin-2",
        frozenset({ScopeItem.MEDICATIONS}),
        "Consultation",
        expires_at,
        store,
        clock,
        lambda: "grant-new",
    )


def test_lists_only_this_patients_grants_newest_first():
    older = replace(
        GRANT, grant_ref="grant-older", granted_at=GRANT.granted_at - timedelta(days=9)
    )
    other = replace(GRANT, grant_ref="grant-other", patient_ref="pat-2")
    store = InMemoryAccessGrantStore((older, GRANT, other))

    refs = [g.grant_ref for g in list_access_grants("pat-1", store)]

    assert refs == ["grant-1", "grant-older"]
    assert list_access_grants("pat-unknown", store) == ()


def test_records_an_active_grant_from_now():
    store = InMemoryAccessGrantStore()

    created = grant(store)

    assert store.get("grant-new") == created
    assert (created.granted_at, created.revoked_at) == (DEMO_NOW, None)
    assert created.status(DEMO_NOW) is GrantStatus.ACTIVE


def test_generates_an_opaque_reference_by_default():
    store = InMemoryAccessGrantStore()

    created = grant_access(
        "pat-1",
        "clin-2",
        frozenset({ScopeItem.MEDICATIONS}),
        "Consultation",
        DEMO_NOW + timedelta(days=1),
        store,
        clock,
    )

    assert created.grant_ref.startswith("grant-") and len(created.grant_ref) == 38


@pytest.mark.parametrize("expires_at", [DEMO_NOW, DEMO_NOW - timedelta(days=1)])
def test_refuses_an_expiry_that_is_not_in_the_future(expires_at):
    store = InMemoryAccessGrantStore()

    with pytest.raises(InvalidAccessGrant):
        grant(store, expires_at)
    assert store.of_patient("pat-1") == ()


def test_revocation_is_recorded_and_kept():
    store = InMemoryAccessGrantStore((GRANT,))

    revoked = revoke_access_grant("pat-1", "grant-1", store, clock)

    assert revoked.revoked_at == DEMO_NOW
    assert list_access_grants("pat-1", store) == (revoked,)


@pytest.mark.parametrize(
    ("patient_ref", "grant_ref"),
    [("pat-1", "grant-unknown"), ("pat-2", "grant-1")],
    ids=["unknown", "another-patients"],
)
def test_an_unknown_or_foreign_grant_is_not_found(patient_ref, grant_ref):
    store = InMemoryAccessGrantStore((GRANT,))

    with pytest.raises(GrantNotFound):
        revoke_access_grant(patient_ref, grant_ref, store, clock)
    assert store.get("grant-1") == GRANT
