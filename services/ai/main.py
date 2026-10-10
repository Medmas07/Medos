from datetime import UTC, datetime

from fastapi import FastAPI

from adapters.inbound.http.ai_provider import create_ai_provider_router
from adapters.inbound.http.clinical_extraction import (
    create_router as create_clinical_extraction_router,
)
from adapters.inbound.http.clinical_extraction import register_problem_handler
from adapters.inbound.http.health import create_health_router
from adapters.inbound.http.hospital_document_review import (
    create_router as create_document_review_router,
)
from adapters.outbound.claude_agent_sdk_provider import ClaudeAgentSdkProvider
from adapters.outbound.fixture_document_reviewer import FixtureDocumentReviewer
from adapters.outbound.fixture_extractor import FixtureClinicalExtractor
from adapters.outbound.mock_ai_provider import DeterministicMockAiProvider
from adapters.outbound.ollama_provider import OllamaAiProvider
from application.ai_provider import AiProvider
from application.extract_clinical_information import (
    ClinicalExtractor,
    ExtractClinicalInformation,
)
from application.fallback_ai_provider import FallbackAiProvider
from application.get_service_status import SERVICE_VERSION
from application.model_clinical_extractor import ModelClinicalExtractor
from application.model_document_reviewer import ModelDocumentReviewer
from application.review_hospital_documents import (
    DocumentReviewer,
    ReviewHospitalDocuments,
)
from infrastructure.settings import (
    ExtractionMode,
    ProviderName,
    ReviewMode,
    Settings,
    load_settings,
)


def _provider(name: ProviderName, settings: Settings) -> AiProvider:
    if name is ProviderName.CLAUDE:
        return ClaudeAgentSdkProvider(
            model=settings.claude_model,
            timeout_seconds=settings.provider_timeout_seconds,
        )
    return OllamaAiProvider(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.provider_timeout_seconds,
    )


def create_app(settings: Settings) -> FastAPI:
    ai_provider: AiProvider
    extractor: ClinicalExtractor
    reviewer: DocumentReviewer
    model_chain = FallbackAiProvider(
        [_provider(n, settings) for n in settings.providers]
    )
    if settings.extraction_mode is ExtractionMode.FIXTURE:
        ai_provider = DeterministicMockAiProvider()
        extractor = FixtureClinicalExtractor()
        extraction = "clinical-extraction:mocked"
    else:
        ai_provider = model_chain
        extractor = ModelClinicalExtractor(model_chain)
        extraction = "clinical-extraction:model"
    # HC-154: chosen on its own, so either capability can run offline.
    if settings.review_mode is ReviewMode.FIXTURE:
        reviewer = FixtureDocumentReviewer()
        review = "hospital-document-review:mocked"
    else:
        reviewer = ModelDocumentReviewer(model_chain)
        review = "hospital-document-review:model"
    capabilities = (extraction, review)

    app = FastAPI(title="AI Services", version=SERVICE_VERSION)
    app.include_router(create_health_router(capabilities))
    app.include_router(
        create_clinical_extraction_router(
            ExtractClinicalInformation(
                extractor=extractor, clock=lambda: datetime.now(UTC)
            )
        )
    )
    app.include_router(
        create_document_review_router(
            ReviewHospitalDocuments(reviewer=reviewer, clock=lambda: datetime.now(UTC))
        )
    )
    app.include_router(create_ai_provider_router(ai_provider))
    register_problem_handler(app)
    return app


app = create_app(load_settings())
