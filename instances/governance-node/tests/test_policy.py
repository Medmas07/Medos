from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from domain.policy import (
    ConsentMode,
    GovernancePolicy,
    InvalidPolicy,
    NoPolicyInEffect,
    PolicyHistory,
    PolicyStatus,
)
from tests.conftest import DEMO_NOW

# The fictional demo policy, as in demo-data/governance.json.
DEMO_POLICY = GovernancePolicy(
    policy_ref="pol-governance-v1",
    version=1,
    effective_from=datetime.fromisoformat("2025-01-01T00:00:00+01:00"),
    title="Politique de gouvernance de démonstration, version 1",
    minimum_rationale_length=20,
    maximum_sync_duration_days=365,
    consent_bases=(
        ("patient_grant", ConsentMode.VERIFIED),
        ("signed_consent_form", ConsentMode.MANUAL),
        ("emergency_override", ConsentMode.MANUAL),
    ),
    maximum_research_validity_months=12,
    minimum_cell_size=10,
)
DEMO_POLICIES = PolicyHistory((DEMO_POLICY,))
LATER = DEMO_NOW + timedelta(days=1)
# A stricter second version, effective the day after the demo date: for tests only.
V2 = replace(
    DEMO_POLICY,
    policy_ref="pol-governance-v2",
    version=2,
    effective_from=LATER,
    title="Stricter test policy",
    minimum_rationale_length=40,
    maximum_sync_duration_days=10,
    consent_bases=(("patient_grant", ConsentMode.VERIFIED),),
    maximum_research_validity_months=6,
    minimum_cell_size=20,
)
TWO_VERSIONS = PolicyHistory((DEMO_POLICY, V2))


def test_the_demo_policy_sits_on_the_documented_limits():
    assert DEMO_POLICY.consent_mode("patient_grant") is ConsentMode.VERIFIED
    assert DEMO_POLICY.consent_mode("signed_consent_form") is ConsentMode.MANUAL
    assert DEMO_POLICY.consent_mode("none") is None


@pytest.mark.parametrize(
    "changes",
    [
        {"policy_ref": "governance-v1"},
        {"version": 0},
        {"effective_from": datetime(2025, 1, 1)},
        {"title": " "},
        # Never looser than the limits the contracts document.
        {"minimum_rationale_length": 19},
        {"maximum_sync_duration_days": 366},
        {"maximum_sync_duration_days": 0},
        {"maximum_research_validity_months": 13},
        {"minimum_cell_size": 9},
        {"consent_bases": ()},
        {"consent_bases": (("none", ConsentMode.MANUAL),)},
        {"consent_bases": (("signed_consent_form", ConsentMode.VERIFIED),)},
        {
            "consent_bases": (
                ("patient_grant", ConsentMode.VERIFIED),
                ("patient_grant", ConsentMode.MANUAL),
            )
        },
    ],
)
def test_invalid_policies(changes):
    with pytest.raises(InvalidPolicy):
        replace(DEMO_POLICY, **changes)


def test_a_stricter_policy_is_valid():
    assert V2.consent_mode("signed_consent_form") is None


def test_picks_the_version_in_effect():
    assert TWO_VERSIONS.in_effect(DEMO_NOW) == DEMO_POLICY
    assert TWO_VERSIONS.in_effect(LATER) == V2
    with pytest.raises(NoPolicyInEffect):
        TWO_VERSIONS.in_effect(DEMO_POLICY.effective_from - timedelta(seconds=1))


def test_status_of_each_version():
    assert [TWO_VERSIONS.status_at(p, DEMO_NOW) for p in TWO_VERSIONS.versions] == [
        PolicyStatus.IN_EFFECT,
        PolicyStatus.SCHEDULED,
    ]
    assert [TWO_VERSIONS.status_at(p, LATER) for p in TWO_VERSIONS.versions] == [
        PolicyStatus.SUPERSEDED,
        PolicyStatus.IN_EFFECT,
    ]
    assert TWO_VERSIONS.policy("pol-governance-v2") == V2
    assert TWO_VERSIONS.policy("pol-unknown") is None


@pytest.mark.parametrize(
    "versions",
    [
        (),
        (V2,),  # numbered from 1
        (DEMO_POLICY, replace(V2, effective_from=DEMO_POLICY.effective_from)),
        (DEMO_POLICY, replace(V2, policy_ref=DEMO_POLICY.policy_ref)),
    ],
)
def test_invalid_histories(versions):
    with pytest.raises(InvalidPolicy):
        PolicyHistory(versions)
