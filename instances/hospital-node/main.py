from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI

from adapters.inbound.http.federation import create_router as create_federation_router
from adapters.inbound.http.health import create_router as create_health_router
from adapters.outbound.fixture_authorization_verifier import (
    FixtureAuthorizationVerifier,
)
from adapters.outbound.fixture_clinical_repository import FixtureClinicalRepository
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
    app = FastAPI(title="Hospital Node", version=NODE_VERSION)
    app.include_router(create_health_router(config.identity, repository))
    app.include_router(
        create_federation_router(config.identity, repository, verifier, clock)
    )
    return app


config = load_config(config_path_from_env())
app = create_app(config)


if __name__ == "__main__":
    import uvicorn

    # Serves on the configured port; `fastapi dev/run --port` ignore it.
    uvicorn.run(app, host="127.0.0.1", port=config.port)
