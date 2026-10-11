"""HC-220: the demo containers boot each hospital's Node from its own mounted files.

These tests rebuild each container's /etc/hospital-node from the compose file's
mounts in a temporary directory and start the app on it, without Docker. Running the
image itself is checked by hand (see the README's Container section).
"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from infrastructure.config import load_config
from main import create_app
from tests.conftest import CONFIG_DIR

NODE_DIR = Path(__file__).resolve().parents[1]
COMPOSE_DIR = NODE_DIR.parents[1] / "infrastructure" / "docker" / "hospital-node"
COMPOSE = yaml.safe_load((COMPOSE_DIR / "compose.yaml").read_text(encoding="utf-8"))
SERVICES = COMPOSE["services"]
CONTAINER_CONFIG = "/etc/hospital-node/node.json"


def mounts(service: dict) -> list[tuple[Path, str, str]]:
    parsed = []
    for volume in service["volumes"]:
        source, target, mode = volume.split(":")
        parsed.append(((COMPOSE_DIR / source).resolve(), target, mode))
    return parsed


def container_root(service: dict, tmp_path: Path) -> Path:
    for source, target, _ in mounts(service):
        destination = tmp_path / target.lstrip("/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    return tmp_path


def test_every_demo_hospital_has_a_container():
    assert set(SERVICES) == {
        path.name.removesuffix(".demo.json") for path in CONFIG_DIR.glob("*.demo.json")
    }


@pytest.mark.parametrize("hospital", sorted(SERVICES))
def test_a_container_boots_its_own_hospital(hospital, tmp_path):
    root = container_root(SERVICES[hospital], tmp_path)
    config = load_config(root / CONTAINER_CONFIG.lstrip("/"))
    demo = load_config(CONFIG_DIR / f"{hospital}.demo.json")

    assert config.identity == demo.identity
    assert config.port == demo.port
    # Refuses to start on a records file held by another organization (HC-113).
    health = TestClient(create_app(config)).get("/health")
    assert health.status_code == 200
    assert health.json()["node_ref"] == demo.identity.node_ref
    assert health.json()["clinical_records"]["mocked"] is True


@pytest.mark.parametrize("hospital", sorted(SERVICES))
def test_a_container_sees_only_its_own_records_read_only(hospital):
    service = SERVICES[hospital]
    parsed = mounts(service)

    assert all(mode == "ro" for _, _, mode in parsed)
    assert {target for _, target, _ in parsed} >= {CONTAINER_CONFIG}
    records = [source for source, target, _ in parsed if "records" in source.parts]
    assert [path.name for path in records] == [f"{hospital}.json"]


@pytest.mark.parametrize("hospital", sorted(SERVICES))
def test_a_container_is_published_on_loopback_at_its_configured_port(hospital):
    port = load_config(CONFIG_DIR / f"{hospital}.demo.json").port

    # Callers are not authenticated, so the demo never publishes on the LAN.
    assert SERVICES[hospital]["ports"] == [f"127.0.0.1:{port}:{port}"]


def test_containers_run_unprivileged_on_a_read_only_filesystem():
    dockerfile = (NODE_DIR / "Dockerfile").read_text(encoding="utf-8")

    assert "\nUSER hospital-node\n" in dockerfile
    assert "@sha256:" in dockerfile.split("FROM ", 1)[1].splitlines()[0]
    for service in SERVICES.values():
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert "no-new-privileges:true" in service["security_opt"]


def test_the_image_holds_no_hospital_configuration_or_tests():
    ignored = (NODE_DIR / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert {"config/", "tests/", ".storage/"} <= set(ignored)
