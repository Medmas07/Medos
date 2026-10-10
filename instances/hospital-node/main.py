from fastapi import FastAPI

from adapters.inbound.http.health import router as health_router
from application.get_node_status import NODE_VERSION

# Per-hospital configuration (HC-112) and clinical APIs (HC-113+) arrive with
# their tickets.
app = FastAPI(title="Hospital Node", version=NODE_VERSION)
app.include_router(health_router)
