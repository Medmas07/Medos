import pytest

from infrastructure.config import Settings


def test_configuration_is_degraded_by_default(monkeypatch):
    monkeypatch.delenv("RESEARCH_GOVERNANCE_URL", raising=False)
    monkeypatch.delenv("RESEARCH_NODE_ENDPOINTS", raising=False)
    settings = Settings.from_environment()
    assert settings.governance_url is None
    assert settings.node_urls == {}


def test_node_endpoint_configuration_is_explicit(monkeypatch):
    monkeypatch.setenv(
        "RESEARCH_NODE_ENDPOINTS",
        '{"org-hospital-a":"http://127.0.0.1:8101"}',
    )
    settings = Settings.from_environment()
    assert settings.node_urls["org-hospital-a"].endswith("8101")


def test_invalid_node_configuration_fails_startup(monkeypatch):
    monkeypatch.setenv("RESEARCH_NODE_ENDPOINTS", "[]")
    with pytest.raises(ValueError):
        Settings.from_environment()
