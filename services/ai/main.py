from datetime import UTC, datetime

from fastapi import FastAPI

from adapters.inbound.http.clinical_extraction import (
    create_router as create_clinical_extraction_router,
)
from adapters.inbound.http.clinical_extraction import register_problem_handler
from adapters.inbound.http.health import router as health_router
from adapters.outbound.fixture_extractor import FixtureClinicalExtractor
from application.extract_clinical_information import ExtractClinicalInformation
from application.get_service_status import SERVICE_VERSION

app = FastAPI(title="AI Services", version=SERVICE_VERSION)
app.include_router(health_router)
app.include_router(
    create_clinical_extraction_router(
        ExtractClinicalInformation(
            extractor=FixtureClinicalExtractor(),
            clock=lambda: datetime.now(UTC),
        )
    )
)
register_problem_handler(app)
