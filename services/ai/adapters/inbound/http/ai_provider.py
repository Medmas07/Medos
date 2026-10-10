from fastapi import APIRouter
from pydantic import BaseModel

from application.ai_provider import AiProvider

PROVIDER_NOTICE = (
    "Configured AI provider chain (ADR-0006). A mock provider is not validated "
    "intelligence, and any AI output is advisory and requires human review."
)


class AiProviderResponse(BaseModel):
    provider_id: str
    model_id: str
    is_mock: bool
    supported_tasks: list[str]
    notice: str


def create_ai_provider_router(provider: AiProvider) -> APIRouter:
    router = APIRouter()

    @router.get("/ai-provider")
    def ai_provider() -> AiProviderResponse:
        descriptor = provider.describe()
        return AiProviderResponse(
            provider_id=descriptor.provider_id,
            model_id=descriptor.model_id,
            is_mock=descriptor.is_mock,
            supported_tasks=sorted(task.value for task in descriptor.supported_tasks),
            notice=PROVIDER_NOTICE,
        )

    return router
