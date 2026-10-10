"""HTTP adapter for the capability discovery part of contracts/federation/node-registry.v1.yaml."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from adapters.inbound.http.node_registry import NodeRefPath, not_found
from application.discover_capabilities import DiscoverNodeCapabilities
from application.node_registry import NodeNotFound
from domain.node_capabilities import DISCOVERY_NOTICE, DiscoveryResult


def to_wire(result: DiscoveryResult) -> dict:
    descriptor = result.descriptor
    return {
        "node_ref": result.node_ref,
        "base_url": result.base_url,
        "outcome": result.outcome.value,
        "checked_at": result.checked_at.isoformat() if result.checked_at else None,
        "detail": result.detail,
        "capabilities": (
            {
                "status": descriptor.status.value,
                "contract_versions": sorted(descriptor.contract_versions),
                "supported_scopes": sorted(
                    s.value for s in descriptor.supported_scopes
                ),
                "mocked": descriptor.mocked,
            }
            if descriptor
            else None
        ),
    }


def create_router(discovery: DiscoverNodeCapabilities) -> APIRouter:
    router = APIRouter()

    @router.post("/v1/registry/discovery")
    def discover_all_nodes() -> JSONResponse:
        results = discovery.discover_all()
        return JSONResponse(
            {"notice": DISCOVERY_NOTICE, "results": [to_wire(r) for r in results]}
        )

    @router.get("/v1/registry/nodes/{node_ref}/capabilities")
    def get_node_capabilities(node_ref: NodeRefPath) -> JSONResponse:
        try:
            return JSONResponse(to_wire(discovery.latest(node_ref)))
        except NodeNotFound:
            return not_found(node_ref)

    @router.post("/v1/registry/nodes/{node_ref}/capabilities")
    def discover_node_capabilities(node_ref: NodeRefPath) -> JSONResponse:
        try:
            return JSONResponse(to_wire(discovery.discover(node_ref)))
        except NodeNotFound:
            return not_found(node_ref)

    return router
