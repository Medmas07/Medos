from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def request(job_ref="job-001", authorization_decision_ref="dec-rar-001"):
    return {
        "job_ref": job_ref,
        "project_ref": "proj-001",
        "authorization_decision_ref": authorization_decision_ref,
        "requested_by": "usr-aymen",
        "target_organizations": ["org-hospital-a", "org-hospital-b"],
    }


def test_job_endpoint_exposes_mocked_distributed_progress_and_result():
    submitted = client.post("/v1/research-jobs", json=request())
    assert submitted.status_code == 202
    assert submitted.json()["status"] == "queued"
    assert submitted.json()["mocked"] is True

    running = client.get("/v1/research-jobs/job-001")
    assert running.json()["status"] == "running"
    assert {stage["status"] for stage in running.json()["stages"][1:3]} == {"running"}

    completed = client.get("/v1/research-jobs/job-001")
    assert completed.json()["status"] == "completed"
    assert completed.json()["result"]["outcome"] == "released"


def test_job_endpoint_keeps_denial_and_not_found_explicit():
    denied = client.post("/v1/research-jobs", json=request("job-denied", "dec-unknown"))
    assert denied.status_code == 202
    assert denied.json()["status"] == "denied"
    assert denied.json()["error"]["code"] == "authorization_denied"
    assert client.get("/v1/research-jobs/missing").status_code == 404
