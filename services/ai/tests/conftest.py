from fastapi.testclient import TestClient

from infrastructure.settings import (
    ExplanationMode,
    ExtractionMode,
    LabMode,
    ReviewMode,
    Settings,
)
from main import create_app

FIXTURE_SETTINGS = Settings(
    extraction_mode=ExtractionMode.FIXTURE,
    review_mode=ReviewMode.FIXTURE,
    lab_mode=LabMode.FIXTURE,
    explanation_mode=ExplanationMode.TEMPLATE,
)


def fixture_client() -> TestClient:
    """App in fixture mode: deterministic, no model is called."""
    return TestClient(create_app(FIXTURE_SETTINGS))
