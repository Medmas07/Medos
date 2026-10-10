import json
from datetime import datetime

import pytest

from adapters.outbound.in_memory_access_grant_store import (
    AccessGrantFixtureError,
    InMemoryAccessGrantStore,
)
from domain.access_grant import GrantStatus
from domain.patient_history import ScopeItem
from infrastructure.config import load_config
from tests.conftest import CONFIG_DIR, DEMO_NOW

ACCESS = load_config(CONFIG_DIR / "hospital-a.demo.json").mock_access_grants


def test_seeds_the_demo_grants():
    grant = InMemoryAccessGrantStore.load(ACCESS).get("grant-a-drx")

    assert (grant.patient_ref, grant.grantee_ref) == ("pat-a", "clin-x")
    assert grant.scope == frozenset(ScopeItem)
    assert grant.granted_at == datetime.fromisoformat("2026-10-10T09:00:00+01:00")
    assert grant.status(DEMO_NOW) is GrantStatus.ACTIVE


def test_keeps_expired_and_revoked_demo_grants_with_their_status():
    store = InMemoryAccessGrantStore.load(ACCESS)

    assert store.get("grant-a-ines").status(DEMO_NOW) is GrantStatus.EXPIRED
    assert store.get("grant-c-ines").status(DEMO_NOW) is GrantStatus.REVOKED


def test_lists_one_patients_grants():
    store = InMemoryAccessGrantStore.load(ACCESS)

    assert {g.grant_ref for g in store.of_patient("pat-a")} == {
        "grant-a-drx",
        "grant-a-ines",
    }


def test_changes_stay_in_this_process(tmp_path):
    copy = tmp_path / "access.json"
    copy.write_bytes(ACCESS.read_bytes())
    store = InMemoryAccessGrantStore.load(copy)

    store.save(store.get("grant-a-drx").revoked(DEMO_NOW))

    assert store.get("grant-a-drx").status(DEMO_NOW) is GrantStatus.REVOKED
    assert copy.read_bytes() == ACCESS.read_bytes()
    # Another node seeded from the same file does not see it.
    assert InMemoryAccessGrantStore.load(copy).get("grant-a-drx").revoked_at is None


def test_refuses_a_fixture_not_marked_fictional(tmp_path):
    access = json.loads(ACCESS.read_text(encoding="utf-8"))
    unmarked = tmp_path / "access.json"
    unmarked.write_text(json.dumps({**access, "fictional": False}))

    with pytest.raises(AccessGrantFixtureError, match="not marked fictional"):
        InMemoryAccessGrantStore.load(unmarked)


def test_refuses_a_malformed_grant(tmp_path):
    access = json.loads(ACCESS.read_text(encoding="utf-8"))
    access["accessGrants"][0]["scope"] = []
    broken = tmp_path / "access.json"
    broken.write_text(json.dumps(access))

    with pytest.raises(AccessGrantFixtureError, match="Invalid access grant"):
        InMemoryAccessGrantStore.load(broken)


def test_refuses_a_missing_fixture(tmp_path):
    with pytest.raises(AccessGrantFixtureError, match="Cannot read"):
        InMemoryAccessGrantStore.load(tmp_path / "absent.json")
