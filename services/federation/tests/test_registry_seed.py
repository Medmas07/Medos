import json
from pathlib import Path

import pytest

from adapters.outbound.in_memory_registration_store import InMemoryRegistrationStore
from application.node_registry import NodeRegistry
from domain.node_registration import InvalidRegistration
from infrastructure.registry_seed import load_seed
from tests.conftest import DEMO_NOW, DEMO_SEED

ORGANIZATIONS = json.loads(
    (
        Path(__file__).resolve().parents[3] / "demo-data" / "organizations.json"
    ).read_text()
)["organizations"]


def registry() -> NodeRegistry:
    return NodeRegistry(store=InMemoryRegistrationStore(), clock=lambda: DEMO_NOW)


def test_demo_seed_matches_the_canonical_demo_organizations():
    seeded = registry()
    assert load_seed(seeded, DEMO_SEED) == 3

    expected = {
        o["node"]["id"]: (o["id"], o["approvalDecisionId"])
        for o in ORGANIZATIONS
        if o["governanceStatus"] == "approved" and o["node"]
    }
    assert {
        r.node_ref: (r.organization_ref, r.approval_decision_ref) for r in seeded.list()
    } == expected


def test_hospital_in_onboarding_is_not_seeded():
    seeded = registry()
    load_seed(seeded, DEMO_SEED)
    assert "org-hospital-c" not in {r.organization_ref for r in seeded.list()}


def test_invalid_seed_stops_startup(tmp_path):
    seed = json.loads(DEMO_SEED.read_text())
    seed["nodes"][0]["contract_versions"] = ["2.0"]
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(seed))
    with pytest.raises(InvalidRegistration):
        load_seed(registry(), path)


def test_seed_is_fictional_and_holds_no_clinical_fields():
    seed = json.loads(DEMO_SEED.read_text())
    assert seed["fictional"] is True
    assert all(
        set(node)
        == {
            "node_ref",
            "organization_ref",
            "base_url",
            "contract_versions",
            "approval_decision_ref",
        }
        for node in seed["nodes"]
    )


def test_registration_times_come_from_the_clock():
    seeded = registry()
    load_seed(seeded, DEMO_SEED)
    assert {r.registered_at for r in seeded.list()} == {DEMO_NOW}
