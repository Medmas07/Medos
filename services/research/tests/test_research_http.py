from fastapi.testclient import TestClient

from main import app
from adapters.inbound.http import research_jobs
from application.research_orchestrator import ResearchOrchestrator


client = TestClient(app)


class NodeDouble:
    def submit(self, node_ref, request):
        if request["authorization"]["decision_ref"] != "dec-rar-001":
            return {"status": "denied", "execution_id": request["execution_id"]}
        return {"status": "accepted", "execution_id": request["execution_id"]}

    def read(self, node_ref, execution_ref):
        return {"status": "completed", "execution_id": execution_ref}


research_jobs.orchestrator = ResearchOrchestrator(
    node_execution=NodeDouble(),
    node_refs=["node-hospital-a", "node-hospital-b"],
)


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

    running = client.get("/v1/research-jobs/job-001")
    assert running.json()["status"] == "running"
    assert {stage["status"] for stage in running.json()["stages"][1:3]} == {"running"}

    completed = client.get("/v1/research-jobs/job-001")
    assert completed.json()["status"] == "completed"
    assert completed.json()["result"]["outcome"] == "released"


def test_job_endpoint_keeps_denial_and_not_found_explicit():
    denied = client.post("/v1/research-jobs", json=request("job-denied", "dec-unknown"))
    assert denied.status_code == 202
    assert client.get("/v1/research-jobs/job-denied").json()["status"] == "denied"
    assert (
        client.get("/v1/research-jobs/job-denied").json()["error"]["code"]
        == "authorization_denied"
    )
    assert client.get("/v1/research-jobs/missing").status_code == 404
