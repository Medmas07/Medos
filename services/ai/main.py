from fastapi import FastAPI

from adapters.inbound.http.health import router as health_router
from application.get_service_status import SERVICE_VERSION

app = FastAPI(title="AI Services", version=SERVICE_VERSION)
app.include_router(health_router)
