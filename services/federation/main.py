import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from adapters.inbound.http.federated_query import (
    create_router,
    register_problem_handler,
)
from adapters.inbound.http.health import SERVICE_VERSION
from adapters.inbound.http.health import create_router as create_health_router
from adapters.inbound.http.node_capabilities import (
    create_router as create_capabilities_router,
)
from adapters.inbound.http.node_registry import create_router as create_registry_router
from adapters.outbound.http_hospital_node_client import HttpHospitalNodeClient
from adapters.outbound.http_node_descriptor_client import HttpNodeDescriptorClient
from adapters.outbound.http_sync_authorization_checker import (
    HttpSyncAuthorizationChecker,
)
from adapters.outbound.in_memory_discovery_store import InMemoryDiscoveryStore
from adapters.outbound.in_memory_registration_store import InMemoryRegistrationStore
from adapters.outbound.simulated_hospital_nodes import SimulatedHospitalNodes
from application.discover_capabilities import DiscoverNodeCapabilities
from application.federate_patient_query import FederatePatientQuery
from application.node_failures import NodeCircuitBreaker, RetryPolicy
from application.node_registry import NodeRegistry
from infrastructure.registry_seed import load_seed, seed_path_from_env

# Suggested Governance Node port (ADR-0003).
DEFAULT_GOVERNANCE_URL = "http://localhost:8200"
# "http": real calls to registered nodes (HC-145). "simulated": MOCKED nodes (HC-141).
NODE_MODES = ("http", "simulated")


def create_app(
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    registry_seed: Path | None = None,
    node_transport=None,
    governance_url: str = DEFAULT_GOVERNANCE_URL,
    governance_transport=None,
    node_mode: str = "http",
    retry_policy: RetryPolicy = RetryPolicy(),
    breaker_clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> FastAPI:
    if node_mode not in NODE_MODES:
        raise ValueError(f"node_mode must be one of {NODE_MODES}, not {node_mode!r}.")
    registry = NodeRegistry(store=InMemoryRegistrationStore(), clock=clock)
    if registry_seed:
        load_seed(registry, registry_seed)
    # Real HTTP calls to each node's registered base_url (HC-143).
    discovery = DiscoverNodeCapabilities(
        registry=registry,
        client=HttpNodeDescriptorClient(transport=node_transport),
        store=InMemoryDiscoveryStore(),
        clock=clock,
    )
    breaker = NodeCircuitBreaker(clock=breaker_clock)
    federate = FederatePatientQuery(
        registry=registry,
        nodes=(
            HttpHospitalNodeClient(
                registry,
                timeout_seconds=retry_policy.attempt_timeout_seconds,
                transport=node_transport,
            )
            if node_mode == "http"
            else SimulatedHospitalNodes(clock=clock)
        ),
        # Real HTTP check with the Governance Node for synchronization decisions (HC-144).
        sync_authorizations=HttpSyncAuthorizationChecker(
            governance_url, transport=governance_transport
        ),
        # Route around nodes whose last check shows they cannot answer (HC-146). Discovery
        # describes real nodes, so it says nothing about simulated ones.
        capabilities=discovery if node_mode == "http" else None,
        # Retries and circuit breaker for real node calls only (HC-147).
        retry=retry_policy if node_mode == "http" else None,
        breaker=breaker if node_mode == "http" else None,
        sleep=sleep,
        clock=clock,
    )
    app = FastAPI(title="Federation Service", version=SERVICE_VERSION)
    app.include_router(create_health_router(node_mode))
    app.include_router(create_registry_router(registry))
    app.include_router(create_capabilities_router(discovery))
    app.include_router(create_router(federate))
    register_problem_handler(app)
    return app


app = create_app(
    registry_seed=seed_path_from_env(),
    governance_url=os.environ.get("FEDERATION_GOVERNANCE_URL", DEFAULT_GOVERNANCE_URL),
    node_mode=os.environ.get("FEDERATION_NODES", "http"),
)
