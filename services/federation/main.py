from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI

from adapters.inbound.http.federated_query import (
    create_router,
    register_problem_handler,
)
from adapters.inbound.http.health import SERVICE_VERSION
from adapters.inbound.http.health import router as health_router
from adapters.outbound.simulated_hospital_nodes import (
    DemoNodeRegistry,
    SimulatedHospitalNodes,
)
from application.federate_patient_query import FederatePatientQuery


def create_app(clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> FastAPI:
    # MOCKED until the node registry (HC-142) and real node-to-node calls (HC-145) exist.
    federate = FederatePatientQuery(
        registry=DemoNodeRegistry(),
        nodes=SimulatedHospitalNodes(clock=clock),
        clock=clock,
    )
    app = FastAPI(title="Federation Service", version=SERVICE_VERSION)
    app.include_router(health_router)
    app.include_router(create_router(federate))
    register_problem_handler(app)
    return app


app = create_app()
