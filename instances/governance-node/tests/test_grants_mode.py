import pytest

from adapters.outbound.in_memory_hospital_applications import SeedError
from main import GRANTS_ENV, HOSPITAL_NODES_ENV, grants_from_env
from tests.conftest import DEMO_DATA


def test_http_is_the_default(monkeypatch):
    monkeypatch.delenv(GRANTS_ENV, raising=False)
    monkeypatch.delenv(HOSPITAL_NODES_ENV, raising=False)

    assert grants_from_env(DEMO_DATA).mode == "http"


def test_the_fixture_is_opt_in(monkeypatch):
    monkeypatch.setenv(GRANTS_ENV, "fixture")

    grants = grants_from_env(DEMO_DATA)
    assert (grants.mode, grants.mocked) == ("fixture", True)


def test_another_mode_stops_startup(monkeypatch):
    monkeypatch.setenv(GRANTS_ENV, "simulated")

    with pytest.raises(SeedError):
        grants_from_env(DEMO_DATA)


def test_an_invalid_node_directory_stops_startup(monkeypatch, tmp_path):
    monkeypatch.delenv(GRANTS_ENV, raising=False)
    monkeypatch.setenv(HOSPITAL_NODES_ENV, str(tmp_path / "missing.json"))

    with pytest.raises(SeedError):
        grants_from_env(DEMO_DATA)
