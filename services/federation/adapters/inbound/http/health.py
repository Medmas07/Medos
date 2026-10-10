from fastapi import APIRouter

SERVICE_NAME = "federation-service"
SERVICE_VERSION = "0.1.0"
MOCK_NOTICE = (
    "MOCKED federation (HC-141). Hospital Nodes are simulated in process from fictional "
    "demo data; this is not node-to-node exchange and not production security. "
    "The Federation Service stores no clinical data."
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
