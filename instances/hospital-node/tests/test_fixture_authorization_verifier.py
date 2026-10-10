import json
from datetime import datetime

import pytest

from adapters.outbound.fixture_authorization_verifier import (
    AuthorizationFixtureError,
    FixtureAuthorizationVerifier,
)
from domain.patient_history import (
    Authorization,
    AuthorizationBasis,
    HistoryQuery,
    Requester,
    ScopeItem,
)
from infrastructure.config import load_config
from tests.conftest import CONFIG_DIR, DEMO_NOW

GRANT = AuthorizationBasis.PATIENT_ACCESS_GRANT
DECISION = AuthorizationBasis.SYNCHRONIZATION_DECISION
# Inside dec-sync-002's validity, which ended on 2026-03-12.
BEFORE_SYNC_002_ENDS = datetime.fromisoformat("2026-01-10T10:00:00+01:00")


def verifier_for(hospital: str) -> FixtureAuthorizationVerifier:
    config = load_config(CONFIG_DIR / f"{hospital}.demo.json")
    return FixtureAuthorizationVerifier.load(
        config.mock_access_grants,
        config.mock_governance_decisions,
        config.identity.organization_ref,
    )


def dr_x_patient_a(**changes) -> HistoryQuery:
    """Dr. X asks for Patient A under grant-a-drx, as in the demo scenario."""
    fields = {
        "query_id": "0b9f6c2e-3d41-4a8e-9f57-1c2d3e4f5a6b",
        "patient_ref": "pat-a",
        "scope": frozenset(ScopeItem),
        "purpose": "Consultation de cardiologie",
        "requested_by": Requester("org-hospital-a", "clin-x"),
        "authorization": Authorization(GRANT, "grant-a-drx", DEMO_NOW),
    }
    return HistoryQuery(**(fields | changes))


def sync_002(**changes) -> HistoryQuery:
    """The private practice asks Hospital B for Patient C's encounters under sync-002."""
    fields = {
        "query_id": "0b9f6c2e-3d41-4a8e-9f57-1c2d3e4f5a6c",
        "patient_ref": "pat-c",
        "scope": frozenset({ScopeItem.ENCOUNTERS}),
        "purpose": "Suivi de l'asthme après passage aux urgences",
        "requested_by": Requester("org-private-practice", "clin-hatem"),
        "authorization": Authorization(DECISION, "dec-sync-002", BEFORE_SYNC_002_ENDS),
    }
    return HistoryQuery(**(fields | changes))


def test_active_grant_allows_its_grantee():
    assert verifier_for("hospital-b").allows(dr_x_patient_a(), DEMO_NOW)


def test_grant_allows_a_narrower_scope():
    narrower = dr_x_patient_a(scope=frozenset({ScopeItem.MEDICATIONS}))

    assert verifier_for("hospital-b").allows(narrower, DEMO_NOW)


@pytest.mark.parametrize(
    "query",
    [
        dr_x_patient_a(requested_by=Requester("org-hospital-a", "clin-ines")),
        dr_x_patient_a(patient_ref="pat-b"),
        dr_x_patient_a(purpose="Recherche"),
        dr_x_patient_a(authorization=Authorization(GRANT, "grant-unknown", DEMO_NOW)),
        dr_x_patient_a(authorization=Authorization(DECISION, "grant-a-drx", DEMO_NOW)),
    ],
    ids=["other-actor", "other-patient", "other-purpose", "unknown-ref", "wrong-basis"],
)
def test_grant_denies_by_default(query):
    assert not verifier_for("hospital-b").allows(query, DEMO_NOW)


def test_grant_denies_after_it_expires():
    after = datetime.fromisoformat("2026-10-24T09:00:00+01:00")

    assert not verifier_for("hospital-b").allows(dr_x_patient_a(), after)


def test_expired_grant_is_denied():
    query = dr_x_patient_a(
        requested_by=Requester("org-hospital-b", "clin-ines"),
        scope=frozenset({ScopeItem.ENCOUNTERS}),
        purpose="Consultation de médecine interne",
        authorization=Authorization(GRANT, "grant-a-ines", DEMO_NOW),
    )

    assert not verifier_for("hospital-b").allows(query, DEMO_NOW)


def test_revoked_grant_is_denied_even_before_its_expiry():
    query = dr_x_patient_a(
        patient_ref="pat-c",
        requested_by=Requester("org-hospital-b", "clin-ines"),
        scope=frozenset({ScopeItem.ENCOUNTERS}),
        purpose="Suivi après passage aux urgences",
        authorization=Authorization(GRANT, "grant-c-ines", DEMO_NOW),
    )
    before_expiry = datetime.fromisoformat("2026-04-01T10:00:00+01:00")

    assert not verifier_for("hospital-b").allows(query, before_expiry)


def test_grant_never_widens_its_scope():
    query = dr_x_patient_a(
        patient_ref="pat-c",
        requested_by=Requester("org-hospital-b", "clin-ines"),
        purpose="Suivi après passage aux urgences",
        scope=frozenset({ScopeItem.ENCOUNTERS, ScopeItem.MEDICATIONS}),
        authorization=Authorization(GRANT, "grant-c-ines", DEMO_NOW),
    )
    before_revocation = datetime.fromisoformat("2026-01-01T10:00:00+01:00")

    assert not verifier_for("hospital-b").allows(query, before_revocation)


def test_approved_decision_allows_its_target_node():
    assert verifier_for("hospital-b").allows(sync_002(), BEFORE_SYNC_002_ENDS)


def test_decision_is_denied_at_a_node_it_does_not_target():
    assert not verifier_for("hospital-a").allows(sync_002(), BEFORE_SYNC_002_ENDS)


@pytest.mark.parametrize(
    "query, at",
    [
        (sync_002(), DEMO_NOW),
        (sync_002(scope=frozenset(ScopeItem)), BEFORE_SYNC_002_ENDS),
        (
            sync_002(requested_by=Requester("org-hospital-a", "clin-x")),
            BEFORE_SYNC_002_ENDS,
        ),
        (
            sync_002(authorization=Authorization(DECISION, "dec-sync-003", DEMO_NOW)),
            BEFORE_SYNC_002_ENDS,
        ),
        (
            sync_002(authorization=Authorization(DECISION, "dec-hospital-b", DEMO_NOW)),
            BEFORE_SYNC_002_ENDS,
        ),
    ],
    ids=[
        "expired",
        "wider-scope",
        "other-requester",
        "rejected-decision",
        "not-a-sync-decision",
    ],
)
def test_decision_denies_by_default(query, at):
    assert not verifier_for("hospital-b").allows(query, at)


def test_refuses_a_fixture_not_marked_fictional(tmp_path):
    config = load_config(CONFIG_DIR / "hospital-a.demo.json")
    access = json.loads(config.mock_access_grants.read_text(encoding="utf-8"))
    unmarked = tmp_path / "access.json"
    unmarked.write_text(json.dumps({**access, "fictional": False}))

    with pytest.raises(AuthorizationFixtureError, match="not marked fictional"):
        FixtureAuthorizationVerifier.load(
            unmarked, config.mock_governance_decisions, "org-hospital-a"
        )


def test_refuses_a_missing_fixture(tmp_path):
    config = load_config(CONFIG_DIR / "hospital-a.demo.json")

    with pytest.raises(AuthorizationFixtureError, match="Cannot read"):
        FixtureAuthorizationVerifier.load(
            tmp_path / "absent.json", config.mock_governance_decisions, "org-hospital-a"
        )
