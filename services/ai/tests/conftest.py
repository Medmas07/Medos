from fastapi.testclient import TestClient

from infrastructure.settings import ExtractionMode, ReviewMode, Settings
from main import create_app

FIXTURE_SETTINGS = Settings(
    extraction_mode=ExtractionMode.FIXTURE, review_mode=ReviewMode.FIXTURE
)


def fixture_client() -> TestClient:
    """App in fixture mode: deterministic, no model is called."""
    return TestClient(create_app(FIXTURE_SETTINGS))
