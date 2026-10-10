"""Composition root for the HC-172 Research Portal boundary."""

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sciagents_adapter import SciAgentsAdapterError, SciAgentsClient
from sciagents_adapter.api import configure_contract_errors, create_router


class UnconfiguredSciAgents:
    """Fail closed when no external endpoint is configured."""

    def submit(self, request: dict[str, Any]) -> dict[str, Any]:
        raise SciAgentsAdapterError(
            "upstream_unavailable", "SciAgents endpoint is not configured.", retryable=True
        )

    def get(self, investigation_id: str) -> dict[str, Any]:
        raise KeyError("investigation_not_found")


upstream_url = os.getenv("SCIAGENTS_URL", "").strip()
portal_origin = os.getenv("RESEARCH_PORTAL_ORIGIN", "http://localhost:5175").strip()
client = SciAgentsClient(upstream_url) if upstream_url else UnconfiguredSciAgents()

app = FastAPI(
    title="SciAgents Integration",
    version="0.2.0",
    description=(
        "D2 server-side boundary to external SciAgents; no clinical data "
        "or browser-to-provider access."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[portal_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)
configure_contract_errors(app)
app.include_router(create_router(client))


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ready" if upstream_url else "degraded",
        "service": "sciagents-integration",
        "depth": "D2",
        "mocked": False,
        "external_endpoint_configured": bool(upstream_url),
        "portal_origin": portal_origin,
    }
