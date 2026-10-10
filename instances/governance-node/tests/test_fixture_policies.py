import json

import pytest

from adapters.outbound.fixture_policies import load_policies
from adapters.outbound.in_memory_hospital_applications import SeedError
from adapters.outbound.in_memory_research import InMemoryResearchStore
from adapters.outbound.in_memory_synchronization import InMemorySynchronizationStore
from tests.conftest import DEMO_DATA
from tests.test_policy import DEMO_POLICIES

GOVERNANCE = DEMO_DATA / "governance.json"


def test_loads_the_demo_policy():
    assert load_policies(GOVERNANCE) == DEMO_POLICIES


def test_seed_decisions_cite_the_demo_policy():
    sync = InMemorySynchronizationStore.load(GOVERNANCE)
    research = InMemoryResearchStore.load(GOVERNANCE, DEMO_DATA / "research.json")

    assert sync.decision("dec-sync-002").policy_ref == "pol-governance-v1"
    assert research.decision("dec-rar-001").policy_ref == "pol-governance-v1"


def write(tmp_path, change):
    data = json.loads(GOVERNANCE.read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / "governance.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def policy(data):
    return data["policies"][0]


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(fictional=False),
        lambda d: d.pop("policies"),
        lambda d: d.update(policies=[]),
        lambda d: policy(d).update(effectiveAt="2025-01-01T00:00:00"),
        lambda d: policy(d)["research"].update(minimumCellSize=5),
        lambda d: policy(d)["synchronization"].update(maximumDurationDays=400),
        lambda d: policy(d)["synchronization"]["consentBases"].update(none="manual"),
        lambda d: policy(d)["synchronization"]["consentBases"].update(
            emergency_override="verified"
        ),
        lambda d: policy(d)["synchronization"]["consentBases"].update(
            patient_grant="trusted"
        ),
        lambda d: policy(d).pop("review"),
        lambda d: d["policies"].append({**policy(d), "id": "pol-governance-v2"}),
    ],
)
def test_refuses_an_unusable_policy(tmp_path, change):
    with pytest.raises(SeedError):
        load_policies(write(tmp_path, change))
