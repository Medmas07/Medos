from fastapi import APIRouter

SERVICE_NAME = "federation-service"
SERVICE_VERSION = "0.1.0"
COMMON_NOTICE = (
    "The node registry (HC-142) is kept in memory, and its Governance approval "
    "references are not verified. The Federation Service stores no clinical data."
)
NODE_NOTICES = {
    "http": (
        "Hospital Nodes are called over real HTTP at their registered base URLs "
        "(HC-145). This is not production security: there is no service authentication."
    ),
    "simulated": (
        "MOCKED Hospital Nodes (HC-141): nodes are simulated in process from fictional "
        "demo data; this is not node-to-node exchange and not production security."
    ),
}


def create_router(node_mode: str) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "nodes": node_mode,
            "mocked": node_mode == "simulated",
            "notice": f"{NODE_NOTICES[node_mode]} {COMMON_NOTICE}",
        }

    return router
