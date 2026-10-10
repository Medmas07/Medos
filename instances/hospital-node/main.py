from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI

from adapters.inbound.http.audit import create_router as create_audit_router
from adapters.inbound.http.federation import create_router as create_federation_router
from adapters.inbound.http.health import create_router as create_health_router
from adapters.outbound.fixture_authorization_verifier import (
    FixtureAuthorizationVerifier,
)
from adapters.outbound.fixture_clinical_repository import FixtureClinicalRepository
from adapters.outbound.in_memory_audit_log import InMemoryAuditLog
from application.get_node_status import NODE_VERSION
from infrastructure.config import HospitalNodeConfig, config_path_from_env, load_config


def _now() -> datetime:
    return datetime.now(UTC)


def create_app(
    config: HospitalNodeConfig, clock: Callable[[], datetime] = _now
) -> FastAPI:
    # MOCKED (HC-113): refuses to start on a records file held by another organization.
    repository = FixtureClinicalRepository.load(
        config.mock_clinical_records, config.identity.organization_ref
    )
    # MOCKED (HC-114): fictional grants and decisions stand in for Governance checks.
    verifier = FixtureAuthorizationVerifier.load(
        config.mock_access_grants,
        config.mock_governance_decisions,
        config.identity.organization_ref,
    )
    # HC-116: real events of the queries handled, kept in memory (persistence is OPEN).
    audit_log = InMemoryAuditLog()
    app = FastAPI(title="Hospital Node", version=NODE_VERSION)
    app.include_router(create_health_router(config.identity, repository))
    app.include_router(
        create_federation_router(
            config.identity, repository, verifier, audit_log, clock
        )
    )
    app.include_router(create_audit_router(config.identity, audit_log))
    return app


config = load_config(config_path_from_env())
app = create_app(config)


if __name__ == "__main__":
    import uvicorn

    # Serves on the configured port; `fastapi dev/run --port` ignore it.
    uvicorn.run(app, host="127.0.0.1", port=config.port)
