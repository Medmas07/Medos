from fastapi import APIRouter

SERVICE_NAME = "federation-service"
SERVICE_VERSION = "0.1.0"
MOCK_NOTICE = (
    "MOCKED Hospital Nodes (HC-141): nodes are simulated in process from fictional demo "
    "data; this is not node-to-node exchange and not production security. The node "
    "registry (HC-142) is real but kept in memory, and its Governance approval "
    "references are not verified. The Federation Service stores no clinical data."
)


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "mocked": True,
        "notice": MOCK_NOTICE,
    }
