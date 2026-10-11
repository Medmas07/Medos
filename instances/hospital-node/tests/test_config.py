import json
from pathlib import Path

import pytest

from infrastructure.config import (
    CONFIG_ENV,
    ConfigError,
    config_path_from_env,
    load_config,
)
from tests.conftest import CONFIG_DIR, DEMO_CONFIGS

ORGANIZATIONS = json.loads(
    (
        Path(__file__).resolve().parents[3] / "demo-data" / "organizations.json"
    ).read_text(encoding="utf-8")
)["organizations"]

VALID = {
    "node_ref": "node-test",
    "organization_ref": "org-test",
    "port": 8199,
    "storage_dir": "storage/test",
    "mock_clinical_records": "records/test.json",
    "mock_access_grants": "access.json",
    "mock_governance_decisions": "governance.json",
    "mock_medication_rules": "medication-rules.json",
}


def write_config(tmp_path: Path, content) -> Path:
    path = tmp_path / "hospital.json"
    path.write_text(content if isinstance(content, str) else json.dumps(content))
    return path


def test_loads_a_valid_configuration(tmp_path):
    config = load_config(write_config(tmp_path, VALID))

    assert config.identity.node_ref == "node-test"
    assert config.identity.organization_ref == "org-test"
    assert config.port == 8199


def test_paths_are_resolved_against_the_config_file(tmp_path):
    config = load_config(write_config(tmp_path, VALID))

    assert config.storage_dir == (tmp_path / "storage" / "test").resolve()
    assert config.mock_clinical_records == (tmp_path / "records/test.json").resolve()
    assert config.mock_access_grants == (tmp_path / "access.json").resolve()


def test_demo_configs_match_the_canonical_demo_nodes():
    expected = {
        o["node"]["id"]: o["id"]
        for o in ORGANIZATIONS
        if o["governanceStatus"] == "approved" and o["node"]
    }
    loaded = [load_config(path) for path in DEMO_CONFIGS]

    assert {
        c.identity.node_ref: c.identity.organization_ref for c in loaded
    } == expected


def test_demo_configs_keep_hospitals_apart():
    loaded = [load_config(path) for path in DEMO_CONFIGS]

    assert len({c.port for c in loaded}) == len(loaded)
    assert len({c.storage_dir for c in loaded}) == len(loaded)
    assert all(c.storage_dir.is_relative_to(CONFIG_DIR.parent) for c in loaded)


def test_hospital_in_onboarding_has_no_demo_config():
    organizations = {load_config(p).identity.organization_ref for p in DEMO_CONFIGS}

    assert "org-hospital-c" not in organizations


def test_missing_environment_variable_stops_startup(monkeypatch):
    monkeypatch.delenv(CONFIG_ENV, raising=False)

    with pytest.raises(ConfigError, match=CONFIG_ENV):
        config_path_from_env()


def test_missing_file_stops_startup(tmp_path):
    with pytest.raises(ConfigError, match="Cannot read"):
        load_config(tmp_path / "absent.json")


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        {k: v for k, v in VALID.items() if k != "node_ref"},
        {**VALID, "prot": 8101},
        {**VALID, "port": 80},
        {**VALID, "port": "8101a"},
        {**VALID, "storage_dir": ""},
        {k: v for k, v in VALID.items() if k != "mock_clinical_records"},
        {k: v for k, v in VALID.items() if k != "mock_access_grants"},
        {**VALID, "mock_governance_decisions": ""},
        {**VALID, "organization_ref": "Hôpital A"},
    ],
    ids=[
        "malformed",
        "missing-field",
        "unknown-field",
        "privileged-port",
        "non-numeric-port",
        "empty-storage",
        "missing-clinical-records",
        "missing-access-grants",
        "empty-governance-decisions",
        "non-opaque-ref",
    ],
)
def test_invalid_configuration_stops_startup(tmp_path, content):
    with pytest.raises(ConfigError, match="Invalid hospital configuration"):
        load_config(write_config(tmp_path, content))
