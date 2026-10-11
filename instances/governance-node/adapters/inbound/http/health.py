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
    # Who may decide (HC-211): "off" (reviewer declared) or "required" (signed in).
    authentication: str
    # Whether authorized federation checks are signed (HC-214): "off" or "ed25519".
    federation_signing: str
    notice: str


def create_router(
    identity: NodeIdentity,
    grants_mode: str,
    authentication_mode: str,
    signing_mode: str = "off",
) -> APIRouter:
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
            authentication=authentication_mode,
            federation_signing=signing_mode,
            notice=node_status.notice,
        )

    return router
