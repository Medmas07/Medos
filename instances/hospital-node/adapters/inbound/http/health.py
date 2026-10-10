from fastapi import APIRouter
from pydantic import BaseModel

from application.get_node_status import get_node_status

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    node: str
    version: str
    capabilities: list[str]
    notice: str


@router.get("/health")
def health() -> HealthResponse:
    node_status = get_node_status()
    return HealthResponse(
        status="ok",
        node=node_status.node,
        version=node_status.version,
        capabilities=list(node_status.capabilities),
        notice=node_status.notice,
    )
