from adapters.inbound.http.ai_provider import PROVIDER_NOTICE
from tests.conftest import fixture_client

client = fixture_client()


def test_ai_provider_reports_the_mock_explicitly():
    response = client.get("/ai-provider")

    assert response.status_code == 200
    assert response.json() == {
        "provider_id": "deterministic-mock",
        "model_id": "none",
        "is_mock": True,
        "supported_tasks": ["explanation", "extraction", "review", "summarization"],
        "notice": PROVIDER_NOTICE,
    }


def test_provider_port_adds_no_ai_capability():
    capabilities = client.get("/health").json()["capabilities"]

    assert not any("provider" in capability for capability in capabilities)
    # Fixture settings call no model: mocked fixtures or the deterministic template.
    assert not any(capability.endswith(":model") for capability in capabilities)
