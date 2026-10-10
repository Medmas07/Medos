from fastapi import APIRouter
from pydantic import BaseModel

from application.get_node_status import get_node_status
from domain.node_identity import NodeIdentity


class HealthResponse(BaseModel):
    status: str
    node: str
    version: str
    node_ref: str
    organization_ref: str
    capabilities: list[str]
    # Where patient grants are evaluated (HC-136): "http" or "fixture" (MOCKED).
    grants: str
    notice: str


def create_router(identity: NodeIdentity, grants_mode: str) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> HealthResponse:
        node_status = get_node_status(identity)
        return HealthResponse(
            status="ok",
            node=node_status.node,
            version=node_status.version,
            node_ref=node_status.node_ref,
            organization_ref=node_status.organization_ref,
            capabilities=list(node_status.capabilities),
            grants=grants_mode,
            notice=node_status.notice,
        )

    return router
