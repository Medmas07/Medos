from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from adapters.inbound.http.federated_query import (
    create_router,
    register_problem_handler,
)
from adapters.inbound.http.health import SERVICE_VERSION
from adapters.inbound.http.health import router as health_router
from adapters.inbound.http.node_capabilities import (
    create_router as create_capabilities_router,
)
from adapters.inbound.http.node_registry import create_router as create_registry_router
from adapters.outbound.http_node_descriptor_client import HttpNodeDescriptorClient
from adapters.outbound.in_memory_discovery_store import InMemoryDiscoveryStore
from adapters.outbound.in_memory_registration_store import InMemoryRegistrationStore
from adapters.outbound.simulated_hospital_nodes import SimulatedHospitalNodes
from application.discover_capabilities import DiscoverNodeCapabilities
from application.federate_patient_query import FederatePatientQuery
from application.node_registry import NodeRegistry
from infrastructure.registry_seed import load_seed, seed_path_from_env


def create_app(
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    registry_seed: Path | None = None,
    node_transport=None,
) -> FastAPI:
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
    # Federated queries stay MOCKED until real node-to-node calls exist (HC-145).
    federate = FederatePatientQuery(
        registry=registry,
        nodes=SimulatedHospitalNodes(clock=clock),
        clock=clock,
    )
    app = FastAPI(title="Federation Service", version=SERVICE_VERSION)
    app.include_router(health_router)
    app.include_router(create_registry_router(registry))
    app.include_router(create_capabilities_router(discovery))
    app.include_router(create_router(federate))
    register_problem_handler(app)
    return app


app = create_app(registry_seed=seed_path_from_env())
