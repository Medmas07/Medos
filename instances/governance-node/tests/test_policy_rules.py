"""The review rules apply the policy they are given, and decisions cite it (HC-135)."""

from dataclasses import replace

import pytest

from domain.hospital_approval import InvalidDecision
from domain.hospital_approval import decide as decide_hospital
from domain.research import decide as decide_research
from domain.synchronization import (
    CheckState,
    Consent,
    ConsentBasis,
    checks,
    max_approved_days,
)
from domain.synchronization import decide as decide_sync
from tests.conftest import DEMO_NOW
from tests.test_hospital_approval import HOSPITAL_C, OLFA, draft
from tests.test_policy import DEMO_POLICY, V2
from tests.test_research import APPROVE, APPROVED_ORGS, RAR
from tests.test_synchronization import APPROVE_13, CONTEXT, SYNC_001

STRICT = replace(V2, effective_from=DEMO_POLICY.effective_from)


def fields(error: InvalidDecision) -> dict[str, str]:
    return {issue.field: issue.message for issue in error.issues}


def test_decisions_cite_the_policy_they_were_decided_under():
    hospital, _ = decide_hospital(HOSPITAL_C, OLFA, draft(), DEMO_POLICY, DEMO_NOW)
    sync, _ = decide_sync(SYNC_001, None, OLFA, APPROVE_13, CONTEXT)
    research, _ = decide_research(
        RAR, None, OLFA, APPROVE, APPROVED_ORGS, DEMO_POLICY, DEMO_NOW
    )

    assert {hospital.policy_ref, sync.policy_ref, research.policy_ref} == {
        "pol-governance-v1"
    }


def test_the_policy_sets_the_minimum_rationale():
    rationale = "Dossier conforme, sous réserve de l’attestation."  # 48 characters
    decide_hospital(HOSPITAL_C, OLFA, draft(rationale=rationale), STRICT, DEMO_NOW)

    with pytest.raises(InvalidDecision) as refused:
        decide_hospital(
            HOSPITAL_C, OLFA, draft(rationale=rationale[:30]), STRICT, DEMO_NOW
        )
    assert fields(refused.value) == {
        "rationale": "The rationale must have at least 40 characters."
    }


def test_the_policy_caps_a_synchronization():
    strict = replace(CONTEXT, policy=STRICT)

    assert max_approved_days(SYNC_001, CONTEXT) == 13  # by the patient grant
    assert max_approved_days(SYNC_001, strict) == 10
    assert checks(SYNC_001, strict)[2].detail == (
        "30 days requested, limited to 10 days by governance policy v2."
    )
    with pytest.raises(InvalidDecision) as refused:
        decide_sync(
            SYNC_001,
            None,
            OLFA,
            replace(APPROVE_13, rationale="x" * 40),
            strict,
        )
    assert fields(refused.value) == {
        "approved_days": "The approved duration must be between 1 and 10 days."
    }
    decision, _ = decide_sync(
        SYNC_001,
        None,
        OLFA,
        replace(APPROVE_13, rationale="x" * 40, approved_days=10),
        strict,
    )
    assert (decision.approved_days, decision.policy_ref) == (10, "pol-governance-v2")


def test_the_policy_decides_which_consent_bases_are_accepted():
    signed = replace(SYNC_001, consent=Consent(ConsentBasis.SIGNED_CONSENT_FORM))

    assert checks(signed, CONTEXT)[1].state is CheckState.MANUAL
    refused = checks(signed, replace(CONTEXT, policy=STRICT))[1]
    assert (refused.state, refused.detail) == (
        CheckState.FAIL,
        "Governance policy v2 does not accept signed_consent_form as a consent basis.",
    )


def test_the_policy_bounds_a_research_approval():
    long_rationale = replace(APPROVE, rationale="x" * 40)

    with pytest.raises(InvalidDecision) as refused:
        decide_research(
            RAR, None, OLFA, long_rationale, APPROVED_ORGS, STRICT, DEMO_NOW
        )
    assert fields(refused.value) == {
        "validity_months": "The validity must be between 1 and 6 months.",
        "minimum_cell_size": "The minimum cell size must be at least 20.",
    }
    decision, _ = decide_research(
        RAR,
        None,
        OLFA,
        replace(long_rationale, validity_months=6, minimum_cell_size=20),
        APPROVED_ORGS,
        STRICT,
        DEMO_NOW,
    )
    assert decision.policy_ref == "pol-governance-v2"
