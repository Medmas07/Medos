"""HC-182/HC-184 D3 Research Service composition root."""

from fastapi import FastAPI

from adapters.inbound.http.research_jobs import create_router
from adapters.outbound.http_boundaries import (
    HttpGovernanceAuthorization,
    HttpHospitalExecution,
)
from application.research_orchestrator import ResearchOrchestrator
from infrastructure.config import Settings

settings = Settings.from_environment()
orchestrator = ResearchOrchestrator(
    authorization=HttpGovernanceAuthorization(
        settings.governance_url, settings.request_timeout_seconds
    ),
    executions=HttpHospitalExecution(
        settings.node_urls, settings.request_timeout_seconds
    ),
)

app = FastAPI(
    title="Research Job Orchestrator",
    version="0.3.0",
    description=(
        "D3 Compute-to-Data orchestration over Governance and Hospital Node "
        "HTTP boundaries with bounded controlled-result aggregation. No submitted "
        "code execution or hospital data access."
    ),
)
app.include_router(create_router(orchestrator))


@app.get("/health")
def health() -> dict:
    configured_nodes = sorted(settings.node_urls)
    ready = bool(settings.governance_url and configured_nodes)
    return {
        "status": "ready" if ready else "degraded",
        "service": "research",
        "depth": "D3",
        "mocked": False,
        "capabilities": ["research_job_orchestration", "controlled_aggregation"],
        "boundaries": {
            "governance_configured": bool(settings.governance_url),
            "configured_organizations": configured_nodes,
        },
    }
