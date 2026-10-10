import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from adapters.inbound.http.audit_events import create_router as create_audit_router
from adapters.inbound.http.health import create_router as create_health_router
from adapters.inbound.http.hospital_approval import (
    create_router as create_hospital_approval_router,
)
from adapters.inbound.http.research_authorization import (
    create_router as create_research_authorization_router,
)
from adapters.inbound.http.research_requests import (
    create_router as create_research_router,
)
from adapters.inbound.http.sync_authorization import (
    create_router as create_sync_authorization_router,
)
from adapters.inbound.http.synchronization_requests import (
    create_router as create_synchronization_router,
)
from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from adapters.outbound.fixture_patient_grants import FixturePatientGrantDirectory
from adapters.outbound.fixture_reviewer_directory import FixtureReviewerDirectory
from adapters.outbound.in_memory_hospital_applications import (
    InMemoryHospitalApplicationStore,
)
from adapters.outbound.in_memory_research import InMemoryResearchStore
from adapters.outbound.in_memory_synchronization import InMemorySynchronizationStore
from application.get_node_status import NODE_VERSION
from domain.node_identity import NodeIdentity

# The fictional Governance / Ethics Authority of the demo dataset
# (demo-data/organizations.json). One Governance Node process (ADR-0003).
DEMO_IDENTITY = NodeIdentity(
    node_ref="node-governance", organization_ref="org-governance"
)
# Suggested Governance Node port (ADR-0003); the Federation Service defaults to it.
PORT = 8200
# Where the fictional seed data is read at startup; the repository's demo-data/ by default.
DEMO_DATA_ENV = "GOVERNANCE_NODE_DEMO_DATA"
DEFAULT_DEMO_DATA = Path(__file__).resolve().parents[2] / "demo-data"


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def create_app(
    identity: NodeIdentity = DEMO_IDENTITY,
    demo_data: Path = DEFAULT_DEMO_DATA,
    clock: Callable[[], datetime] = _now,
) -> FastAPI:
    # HC-131: in memory, seeded from fictional applications; decisions lost on restart.
    applications = InMemoryHospitalApplicationStore.load(demo_data / "governance.json")
    reviewers = FixtureReviewerDirectory.load(demo_data / "people.json")
    # HC-132: in memory, seeded from fictional requests; lost on restart.
    synchronizations = InMemorySynchronizationStore.load(demo_data / "governance.json")
    # MOCKED (HC-132): patient grants belong to the Hospital Nodes (HC-115); until
    # consent governance (HC-136), the Node reads the fictional seed grants.
    grants = FixturePatientGrantDirectory.load(demo_data / "access.json")
    # HC-133: in memory, seeded from fictional requests and projects; lost on restart.
    research = InMemoryResearchStore.load(
        demo_data / "governance.json", demo_data / "research.json"
    )
    # HC-134: in memory, seeded from fictional events; runtime events lost on restart.
    audit = InMemoryAuditTrail.load(demo_data / "governance.json")
    app = FastAPI(title="Governance Node", version=NODE_VERSION)
    app.include_router(create_health_router(identity))
    app.include_router(
        create_hospital_approval_router(applications, reviewers, audit, clock)
    )
    app.include_router(
        create_synchronization_router(
            synchronizations, reviewers, grants, applications, audit, clock
        )
    )
    app.include_router(create_sync_authorization_router(synchronizations, audit, clock))
    app.include_router(
        create_research_router(research, reviewers, applications, audit, clock)
    )
    app.include_router(create_research_authorization_router(research, audit, clock))
    app.include_router(create_audit_router(identity, audit))
    return app


app = create_app(demo_data=Path(os.environ.get(DEMO_DATA_ENV, DEFAULT_DEMO_DATA)))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)
