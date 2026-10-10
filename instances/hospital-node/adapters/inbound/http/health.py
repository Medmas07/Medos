from fastapi import APIRouter
from pydantic import BaseModel

from application.clinical_repository import ClinicalRepository
from application.get_node_status import get_node_status
from domain.node_identity import NodeIdentity


class ClinicalRecordsSummary(BaseModel):
    mocked: bool
    encounters: int
    medications: int
    lab_reports: int


class HealthResponse(BaseModel):
    status: str
    node: str
    version: str
    node_ref: str
    organization_ref: str
    capabilities: list[str]
    clinical_records: ClinicalRecordsSummary
    notice: str


def create_router(identity: NodeIdentity, repository: ClinicalRepository) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> HealthResponse:
        node_status = get_node_status(identity, repository)
        records = node_status.clinical_records
        return HealthResponse(
            status="ok",
            node=node_status.node,
            version=node_status.version,
            node_ref=node_status.node_ref,
            organization_ref=node_status.organization_ref,
            capabilities=list(node_status.capabilities),
            clinical_records=ClinicalRecordsSummary(
                mocked=records.mocked,
                encounters=records.encounters,
                medications=records.medications,
                lab_reports=records.lab_reports,
            ),
            notice=node_status.notice,
        )

    return router
