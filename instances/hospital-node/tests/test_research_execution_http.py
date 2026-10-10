from fastapi.testclient import TestClient

from infrastructure.config import load_config
from main import create_app
from tests.conftest import CONFIG_DIR, DEMO_NOW


def client_for(hospital="hospital-a"):
    return TestClient(
        create_app(
            load_config(CONFIG_DIR / f"{hospital}.demo.json"),
            clock=lambda: DEMO_NOW,
        )
    )


def request(execution_id="job-001-exec-a"):
    return {
        "execution_id": execution_id,
        "job_ref": "job-001",
        "project_ref": "proj-001",
        "target": {
            "node_ref": "node-hospital-a",
            "organization_ref": "org-hospital-a",
        },
        "submitted_by": {
            "organization_ref": "org-platform",
            "actor_ref": "usr-aymen",
        },
        "purpose": "Aggregate cardiometabolic risk research",
        "authorization": {
            "decision_ref": "dec-rar-001",
            "authority_organization_ref": "org-governance",
            "valid_until": "2026-12-31T23:59:59+01:00",
            "approved_organization_refs": ["org-hospital-a", "org-hospital-b"],
            "approved_variables": ["hba1c"],
        },
        "data_scope": {
            "population": {
                "encounter_from": "2024-01-01",
                "encounter_to": "2026-12-31",
            },
            "variables": ["hba1c"],
        },
        "algorithm": {
            "language": "python",
            "artifact_ref": "notebook://nb-001/cell/nb-001-cell-2",
            "sha256": "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801",
            "entrypoint": "compute",
        },
        "output_policy": {
            "kind": "aggregate_table",
            "minimum_cell_size": 10,
            "require_disclosure_review": True,
        },
    }


def test_executes_inside_hospital_boundary_and_suppresses_small_cells():
    client = client_for()
    submitted = client.post("/v1/research-executions", json=request())
    assert submitted.status_code == 202
    assert submitted.json()["mocked"] is True

    completed = client.get("/v1/research-executions/job-001-exec-a")
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "completed"
    assert body["result"]["outcome"] == "suppressed"
    assert body["result"]["rows"] == []
    assert body["result"]["provenance"]["source_node_ref"] == "node-hospital-a"
    assert "pat-a" not in completed.text and "pat-b" not in completed.text


def test_empty_failed_denied_conflict_and_not_found_are_explicit():
    client = client_for()

    empty_request = request("job-empty-exec-a")
    empty_request["data_scope"]["population"] = {"encounter_from": "2030-01-01"}
    assert client.post("/v1/research-executions", json=empty_request).status_code == 202
    empty = client.get("/v1/research-executions/job-empty-exec-a").json()
    assert empty["result"]["outcome"] == "empty"

    failed_request = request("job-failed-exec-a")
    failed_request["data_scope"]["population"]["age_min"] = 40
    assert (
        client.post("/v1/research-executions", json=failed_request).status_code == 202
    )
    failed = client.get("/v1/research-executions/job-failed-exec-a").json()
    assert failed["status"] == "failed"
    assert failed["error"]["code"] == "execution_failed"

    denied_request = request("job-denied-exec-a")
    denied_request["target"]["organization_ref"] = "org-hospital-b"
    denied = client.post("/v1/research-executions", json=denied_request)
    assert denied.status_code == 403
    assert denied.json()["code"] == "scope_denied"

    original = request("job-conflict-exec-a")
    assert client.post("/v1/research-executions", json=original).status_code == 202
    changed = request("job-conflict-exec-a")
    changed["purpose"] = "Different purpose"
    assert client.post("/v1/research-executions", json=changed).status_code == 409

    assert client.get("/v1/research-executions/missing").status_code == 404


def test_invalid_and_expired_requests_fail_before_local_data_access():
    client = client_for()
    invalid = request("job-invalid-exec-a")
    invalid["output_policy"]["kind"] = "raw_records"
    assert client.post("/v1/research-executions", json=invalid).status_code == 400

    expired = request("job-expired-exec-a")
    expired["authorization"]["valid_until"] = "2026-10-09T23:59:59+01:00"
    response = client.post("/v1/research-executions", json=expired)
    assert response.status_code == 403
    assert response.json()["code"] == "authorization_expired"
