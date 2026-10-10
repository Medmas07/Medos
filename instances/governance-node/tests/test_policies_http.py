"""The governance policy API against contracts/api/governance/governance-policies.v1.yaml.

And the engine at work in the running Node: with a stricter version scheduled for the
day after the demo date, the same request is reviewed and decided under version 1 today
and version 2 tomorrow, while decisions already made keep citing version 1.
"""

import json
import shutil
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import DEMO_DATA, DEMO_NOW
from tests.test_synchronization_http import (
    APPROVE_001,
    SYNC,
    Clock,
    check,
    example,
    load,
)

POL = load("api/governance/governance-policies.v1.yaml")
LIST = POL["paths"]["/v1/policies"]["get"]
DETAIL = POL["paths"]["/v1/policies/{policy_ref}"]["get"]
SYNC_DETAIL = SYNC["paths"]["/v1/synchronization-requests/{request_ref}"]["get"]
SYNC_DECIDE = SYNC["paths"]["/v1/synchronization-requests/{request_ref}/decision"][
    "post"
]
TOMORROW = DEMO_NOW + timedelta(days=1)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(demo_data=DEMO_DATA, clock=Clock()))


def test_lists_and_reads_the_demo_policy(client):
    assert check(client.get("/v1/policies"), POL, LIST, 200) == example(
        POL, LIST, 200, "demo"
    )
    assert check(client.get("/v1/policies/pol-governance-v1"), POL, DETAIL, 200) == (
        example(POL, DETAIL, 200, "v1")
    )
    assert check(client.get("/v1/policies/pol-unknown"), POL, DETAIL, 404) == example(
        POL, DETAIL, 404, "unknown"
    )


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def two_versions(tmp_path, clock) -> TestClient:
    """The demo data with a stricter version 2 effective tomorrow."""
    data = tmp_path / "demo-data"
    shutil.copytree(DEMO_DATA, data)
    governance = json.loads((data / "governance.json").read_text(encoding="utf-8"))
    v1 = governance["policies"][0]
    governance["policies"].append(
        {
            **v1,
            "id": "pol-governance-v2",
            "version": 2,
            "effectiveAt": TOMORROW.isoformat(),
            "title": "Politique de test plus stricte",
            "review": {"minimumRationaleLength": 40},
            "synchronization": {
                "maximumDurationDays": 10,
                "consentBases": {"patient_grant": "verified"},
            },
        }
    )
    (data / "governance.json").write_text(json.dumps(governance), encoding="utf-8")
    return TestClient(create_app(demo_data=data, clock=clock))


def statuses(client) -> dict[str, str]:
    body = check(client.get("/v1/policies"), POL, LIST, 200)
    return {p["policy_ref"]: p["status"] for p in body["policies"]}


def test_a_new_version_takes_effect_at_its_date(two_versions, clock):
    assert statuses(two_versions) == {
        "pol-governance-v2": "scheduled",
        "pol-governance-v1": "in_effect",
    }
    clock.now = TOMORROW
    assert statuses(two_versions) == {
        "pol-governance-v2": "in_effect",
        "pol-governance-v1": "superseded",
    }


def test_the_running_node_reviews_and_decides_under_the_version_in_effect(
    two_versions, clock
):
    today = check(
        two_versions.get("/v1/synchronization-requests/sync-001"),
        SYNC,
        SYNC_DETAIL,
        200,
    )
    assert today["max_approved_days"] == 13  # by the patient grant, under v1

    clock.now = TOMORROW
    tomorrow = check(
        two_versions.get("/v1/synchronization-requests/sync-001"),
        SYNC,
        SYNC_DETAIL,
        200,
    )
    assert tomorrow["max_approved_days"] == 10
    assert tomorrow["checks"][2]["detail"] == (
        "30 days requested, limited to 10 days by governance policy v2."
    )

    refused = check(
        two_versions.post(
            "/v1/synchronization-requests/sync-001/decision",
            # Enough for version 1 (20 characters), not for version 2 (40).
            json={
                **APPROVE_001,
                "approved_days": 12,
                "rationale": "Finalité de soins, autorisée.",
            },
        ),
        SYNC,
        SYNC_DECIDE,
        422,
    )
    assert {i["field"] for i in refused["issues"]} == {"rationale", "approved_days"}

    decision = check(
        two_versions.post(
            "/v1/synchronization-requests/sync-001/decision",
            json={
                **APPROVE_001,
                "approved_days": 10,
                "rationale": "Finalité de soins, périmètre limité, autorisation active.",
            },
        ),
        SYNC,
        SYNC_DECIDE,
        201,
    )
    assert decision["policy_ref"] == "pol-governance-v2"

    # A decision made before version 2 keeps citing version 1.
    earlier = two_versions.get("/v1/synchronization-requests/sync-002").json()
    assert earlier["decision"]["policy_ref"] == "pol-governance-v1"


def test_a_decision_today_cites_version_1(client):
    decision = check(
        client.post("/v1/synchronization-requests/sync-001/decision", json=APPROVE_001),
        SYNC,
        SYNC_DECIDE,
        201,
    )

    assert decision["policy_ref"] == "pol-governance-v1"
