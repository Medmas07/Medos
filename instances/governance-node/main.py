import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from adapters.inbound.http.health import create_router as create_health_router
from adapters.inbound.http.hospital_approval import (
    create_router as create_hospital_approval_router,
)
from adapters.outbound.fixture_reviewer_directory import FixtureReviewerDirectory
from adapters.outbound.in_memory_hospital_applications import (
    InMemoryHospitalApplicationStore,
)
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
    app = FastAPI(title="Governance Node", version=NODE_VERSION)
    app.include_router(create_health_router(identity))
    app.include_router(create_hospital_approval_router(applications, reviewers, clock))
    return app


app = create_app(demo_data=Path(os.environ.get(DEMO_DATA_ENV, DEFAULT_DEMO_DATA)))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)
