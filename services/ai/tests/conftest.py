from fastapi.testclient import TestClient

from infrastructure.settings import ExtractionMode, Settings
from main import create_app

FIXTURE_SETTINGS = Settings(extraction_mode=ExtractionMode.FIXTURE)


def fixture_client() -> TestClient:
    """App in fixture mode: deterministic, no model is called."""
    return TestClient(create_app(FIXTURE_SETTINGS))
