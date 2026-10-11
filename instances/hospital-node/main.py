from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI

from adapters.inbound.http.access_grants import (
    create_router as create_access_grants_router,
)
from adapters.inbound.http.audit import create_router as create_audit_router
from adapters.inbound.http.federation import create_router as create_federation_router
from adapters.inbound.http.health import create_router as create_health_router
from adapters.inbound.http.medication_safety import (
    create_router as create_medication_safety_router,
)
from adapters.inbound.http.research_executions import (
    create_router as create_research_executions_router,
)
from adapters.outbound.fixture_authorization_verifier import (
    FixtureAuthorizationVerifier,
)
from adapters.outbound.ai_services_warning_explainer import AiServicesWarningExplainer
from adapters.outbound.ed25519_authorization_reader import Ed25519AuthorizationReader
from adapters.outbound.fixture_clinical_repository import FixtureClinicalRepository
from adapters.outbound.fixture_interaction_rules import FixtureInteractionRuleSource
from adapters.outbound.validated_snapshot_rules import (
    ONC_HIGH_PRIORITY_2012,
    ValidatedSnapshotRuleSource,
)
from adapters.outbound.in_memory_access_grant_store import InMemoryAccessGrantStore
from adapters.outbound.in_memory_audit_log import InMemoryAuditLog
from adapters.outbound.in_memory_research_execution_store import (
    InMemoryResearchExecutionStore,
)
from adapters.outbound.fixture_research_data_source import FixtureResearchDataSource
from adapters.outbound.isolated_research_sandbox import IsolatedResearchSandbox
from application.authorization_verifier import (
    AuthorizationVerifier,
    SignedDecisionVerifier,
)
from application.check_medication_safety import CheckMedicationSafety
from application.research_execution_agent import ResearchExecutionAgent
from application.get_node_status import NODE_VERSION
from infrastructure.config import HospitalNodeConfig, config_path_from_env, load_config


def _now() -> datetime:
    return datetime.now(UTC)


def create_app(
    config: HospitalNodeConfig,
    clock: Callable[[], datetime] = _now,
    new_grant_ref: Callable[[], str] | None = None,
) -> FastAPI:
    # MOCKED (HC-113): refuses to start on a records file held by another organization.
    repository = FixtureClinicalRepository.load(
        config.mock_clinical_records, config.identity.organization_ref
    )
    # MOCKED (HC-115): seeded from fictional grants; changes are kept in memory only.
    access_grants = InMemoryAccessGrantStore.load(config.mock_access_grants)
    # MOCKED (HC-114): fictional decisions and the grant store stand in for Governance.
    verifier: AuthorizationVerifier = FixtureAuthorizationVerifier.load(
        access_grants,
        config.mock_governance_decisions,
        config.identity.organization_ref,
    )
    synchronization_decisions = "fixture"
    if config.governance_public_key:
        # HC-214: synchronization decisions only with a Governance-signed authorization,
        # verified here; patient access grants still from this node's grant store.
        verifier = SignedDecisionVerifier(
            Ed25519AuthorizationReader.load(config.governance_public_key),
            config.governance_organization_ref,
            config.identity.organization_ref,
            others=verifier,
        )
        synchronization_decisions = "signed"
    # HC-116: real events of the queries handled, kept in memory (persistence is OPEN).
    audit_log = InMemoryAuditLog()
    research_data = FixtureResearchDataSource(config.identity, repository)
    research_agent = ResearchExecutionAgent(
        config.identity,
        IsolatedResearchSandbox(research_data),
        InMemoryResearchExecutionStore(),
    )
    rule_source: FixtureInteractionRuleSource | ValidatedSnapshotRuleSource
    if config.medication_rule_source == "onc_high_priority_2012":
        # HC-163: the validated ONC high-priority list; real drugs only, not mocked.
        rule_source = ValidatedSnapshotRuleSource.load(ONC_HIGH_PRIORITY_2012)
    else:
        # MOCKED (HC-162): fictional deterministic rules for the canonical demo.
        rule_source = FixtureInteractionRuleSource.load(config.mock_medication_rules)
    app = FastAPI(title="Hospital Node", version=NODE_VERSION)
    app.include_router(
        create_health_router(config.identity, repository, synchronization_decisions)
    )
    app.include_router(
        create_federation_router(
            config.identity, repository, verifier, audit_log, clock
        )
    )
    app.include_router(create_audit_router(config.identity, audit_log))
    app.include_router(
        create_access_grants_router(
            config.identity, access_grants, clock, new_grant_ref
        )
    )
    app.include_router(create_research_executions_router(research_agent, clock))
    app.include_router(
        create_medication_safety_router(
            CheckMedicationSafety(
                rule_source,
                clock,
                # HC-164: advisory explanations, only when this hospital opts in.
                explainer=AiServicesWarningExplainer(config.ai_services_url)
                if config.ai_services_url
                else None,
            )
        )
    )
    return app


config = load_config(config_path_from_env())
app = create_app(config)


if __name__ == "__main__":
    import uvicorn

    # Serves on the configured port; `fastapi dev/run --port` ignore it.
    uvicorn.run(app, host="127.0.0.1", port=config.port)
