from fastapi import FastAPI

from adapters.inbound.http.ai_provider import create_ai_provider_router
from adapters.inbound.http.health import router as health_router
from adapters.outbound.mock_ai_provider import DeterministicMockAiProvider
from application.get_service_status import SERVICE_VERSION

# The only provider until an ADR selects a real one (HC-153).
ai_provider = DeterministicMockAiProvider()

app = FastAPI(title="AI Services", version=SERVICE_VERSION)
app.include_router(health_router)
app.include_router(create_ai_provider_router(ai_provider))
