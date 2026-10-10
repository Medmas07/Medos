from dataclasses import replace

import pytest

from application.hospital_approval import decide_application
from application.policy import PolicyNotFound, get_policy, list_policies
from domain.policy import PolicyStatus
from tests.conftest import DEMO_NOW
from tests.test_audit_use_cases import FakeAuditTrail
from tests.test_hospital_approval_use_cases import (
    APPROVE,
    STORE_APPS,
    FakeReviewers,
    FakeStore,
)
from tests.test_policy import DEMO_POLICY, LATER, TWO_VERSIONS, V2


def test_lists_the_latest_version_first_with_its_status():
    assert list_policies(TWO_VERSIONS, DEMO_NOW) == [
        (V2, PolicyStatus.SCHEDULED),
        (DEMO_POLICY, PolicyStatus.IN_EFFECT),
    ]
    assert get_policy("pol-governance-v1", TWO_VERSIONS, LATER) == (
        DEMO_POLICY,
        PolicyStatus.SUPERSEDED,
    )
    with pytest.raises(PolicyNotFound):
        get_policy("pol-unknown", TWO_VERSIONS, DEMO_NOW)


@pytest.mark.parametrize(
    "now, cited", [(DEMO_NOW, "pol-governance-v1"), (LATER, "pol-governance-v2")]
)
def test_a_decision_applies_and_cites_the_version_in_effect_when_decided(now, cited):
    decision = decide_application(
        "app-review-old",
        "usr-olfa",
        replace(APPROVE, rationale="x" * 40),  # long enough for both versions
        FakeStore(STORE_APPS),
        FakeReviewers(),
        TWO_VERSIONS,
        FakeAuditTrail(),
        lambda: now,
    )

    assert decision.policy_ref == cited
