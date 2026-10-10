from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapters.inbound.http.research_jobs import create_router
from application.research_orchestrator import ResearchOrchestrator
from domain.research_job import AuthorizationDecision, ExecutionStatus, NodeExecution


class AuthorizationStub:
    def check(self, job):
        return AuthorizationDecision(
            job.authorization_decision_ref,
            True,
            job.target_organizations,
            tuple(job.data_scope["variables"]),
            "org-governance",
            "2099-12-31T23:59:59+01:00",
        )


class ExecutionStub:
    def __init__(self, suppressed_organization=None):
        self.suppressed_organization = suppressed_organization

    def submit(self, job, organization_ref, authorization):
        return NodeExecution(
            f"{job.job_ref}-exec-{organization_ref}",
            organization_ref,
            ExecutionStatus.ACCEPTED,
        )

    def read(self, execution):
        execution.status = ExecutionStatus.COMPLETED
        if execution.organization_ref == self.suppressed_organization:
            execution.mocked = True
            execution.result = {
                "outcome": "suppressed",
                "columns": [],
                "rows": [],
                "disclosure": {"status": "suppressed", "minimum_cell_size": 10},
                "provenance": {
                    "algorithm_sha256": "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801",
                    "authorization_decision_ref": "dec-rar-001",
                    "source_organization_ref": execution.organization_ref,
                },
            }
            return execution
        execution.result = {
            "outcome": "released",
            "columns": ["participant_count", "hba1c_above_7_pct"],
            "rows": [[42, 25.0]],
            "disclosure": {"status": "passed", "minimum_cell_size": 10},
            "provenance": {
                "algorithm_sha256": "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801",
                "authorization_decision_ref": "dec-rar-001",
                "source_organization_ref": execution.organization_ref,
            },
        }
        return execution


app = FastAPI()
app.include_router(
    create_router(ResearchOrchestrator(AuthorizationStub(), ExecutionStub()))
)
client = TestClient(app)


def request(job_ref="job-http-001"):
    return {
        "job_ref": job_ref,
        "project_ref": "proj-001",
        "authorization_decision_ref": "dec-rar-001",
        "requested_by": "usr-aymen",
        "purpose": "Aggregate cardiometabolic risk research",
        "target_organizations": ["org-hospital-a", "org-hospital-b"],
        "data_scope": {
            "population": {"age_min": 40, "age_max": 79},
            "variables": ["age_band", "hba1c"],
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


def test_job_api_exposes_controlled_aggregation():
    submitted = client.post("/v1/research-jobs", json=request())
    assert submitted.status_code == 202
    assert submitted.json()["status"] == "running"
    assert submitted.json()["mocked"] is False

    completed = client.get("/v1/research-jobs/job-http-001")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert len(completed.json()["executions"]) == 2
    assert completed.json()["aggregation"]["status"] == "released"
    assert completed.json()["aggregation"]["rows"] == [[84, 25.0]]


def test_job_api_has_validation_and_not_found_states():
    invalid = request("job-invalid")
    invalid["target_organizations"] = []
    assert client.post("/v1/research-jobs", json=invalid).status_code == 422
    assert client.get("/v1/research-jobs/missing").status_code == 404


def test_job_api_shows_partial_coverage_without_reconstructing_suppressed_cells():
    partial_app = FastAPI()
    partial_app.include_router(
        create_router(
            ResearchOrchestrator(
                AuthorizationStub(),
                ExecutionStub(suppressed_organization="org-hospital-b"),
            )
        )
    )
    partial_client = TestClient(partial_app)
    assert (
        partial_client.post(
            "/v1/research-jobs", json=request("job-http-partial")
        ).status_code
        == 202
    )

    response = partial_client.get("/v1/research-jobs/job-http-partial")
    assert response.status_code == 200
    aggregation = response.json()["aggregation"]
    assert aggregation["status"] == "partial"
    assert aggregation["rows"] == [[42, 25.0]]
    assert aggregation["excluded_organization_refs"] == ["org-hospital-b"]
    assert aggregation["mocked"] is True


def test_job_reference_cannot_be_reused_for_another_request():
    original = request("job-conflict")
    assert client.post("/v1/research-jobs", json=original).status_code == 202
    changed = request("job-conflict")
    changed["purpose"] = "A different purpose"
    conflict = client.post("/v1/research-jobs", json=changed)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "research_job_ref_conflict"
