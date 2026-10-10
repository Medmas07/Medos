from fastapi.testclient import TestClient

from domain.node_status import SKELETON_NOTICE
from infrastructure.config import load_config
from main import create_app
from tests.conftest import CONFIG_DIR


def client_for(hospital: str) -> TestClient:
    return TestClient(create_app(load_config(CONFIG_DIR / f"{hospital}.demo.json")))


def test_health_reports_the_configured_hospital():
    response = client_for("hospital-b").get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "node": "hospital-node",
        "version": "0.2.0",
        "node_ref": "node-hospital-b",
        "organization_ref": "org-hospital-b",
        "capabilities": [
            "patient_history",
            "audit_events",
            "access_grants",
            "research_execution",
        ],
        "clinical_records": {
            "mocked": True,
            "encounters": 2,
            "medications": 1,
            "lab_reports": 1,
        },
        "notice": SKELETON_NOTICE,
    }


def test_each_instance_reports_only_its_own_hospital():
    refs = {
        client_for(h).get("/health").json()["node_ref"]
        for h in ("hospital-a", "hospital-b", "private-practice")
    }

    assert refs == {"node-hospital-a", "node-hospital-b", "node-private-practice"}


def test_health_rejects_non_get_methods():
    assert client_for("hospital-a").post("/health").status_code == 405
