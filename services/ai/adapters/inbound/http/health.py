from fastapi import APIRouter
from pydantic import BaseModel

from application.get_service_status import get_service_status


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    capabilities: list[str]
    notice: str


def create_health_router(capabilities: tuple[str, ...]) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> HealthResponse:
        service_status = get_service_status(capabilities)
        return HealthResponse(
            status="ok",
            service=service_status.service,
            version=service_status.version,
            capabilities=list(service_status.capabilities),
            notice=service_status.notice,
        )

    return router
