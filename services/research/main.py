"""D3 Research Service composition root."""

import os
from fastapi import FastAPI

from adapters.inbound.http import research_jobs
from adapters.outbound.hospital_node_http import HttpHospitalNodeExecutionAdapter
from application.research_orchestrator import ResearchOrchestrator

app = FastAPI(
    title="Research Service (D3)",
    version="0.1.0",
    description=(
        "D3 orchestration over the versioned Hospital Node execution contract. "
        "The service does not access hospital databases."
    ),
)
node_urls = {
    ref: url
    for ref, url in {
        "node-hospital-a": os.getenv("HOSPITAL_NODE_A_URL"),
        "node-hospital-b": os.getenv("HOSPITAL_NODE_B_URL"),
    }.items()
    if url
}
research_jobs.orchestrator = ResearchOrchestrator(
    node_execution=HttpHospitalNodeExecutionAdapter(node_urls),
    node_refs=list(node_urls),
)
app.include_router(research_jobs.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "research", "configured_nodes": list(node_urls)}
