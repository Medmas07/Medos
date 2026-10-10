import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sciagents_adapter import SciAgentsAdapterError, SciAgentsClient
from sciagents_adapter.api import configure_contract_errors, create_router

REQUEST = {
    "project_ref": "proj-001",
    "requested_by": "usr-aymen",
    "question": "Question fictive.",
    "language": "fr",
    "concepts": [{"label": "Metformin"}, {"label": "Diabetes"}],
}


class StubClient:
    def __init__(self):
        self.submitted = None

    def submit(self, request):
        self.submitted = request
        return {"investigation_id": "0b6f5a1e-3c2d-4e7f-9a8b-1c2d3e4f5a6b", "status": "queued"}

    def get(self, investigation_id):
        if investigation_id == "00000000-0000-4000-8000-000000000000":
            raise KeyError("investigation_not_found")
        return {"investigation_id": investigation_id, "status": "running"}


def api(client):
    app = FastAPI()
    configure_contract_errors(app)
    app.include_router(create_router(client))
    return TestClient(app)


def test_submit_exposes_the_contract_and_location_header():
    stub = StubClient()
    response = api(stub).post("/v1/investigations", json=REQUEST)
    assert response.status_code == 202
    assert response.headers["location"].endswith(response.json()["investigation_id"])
    assert stub.submitted == REQUEST


def test_request_rejects_extra_or_missing_concepts_before_the_adapter():
    invalid = {**REQUEST, "patient_ref": "patient-a"}
    assert api(StubClient()).post("/v1/investigations", json=invalid).status_code == 400
    assert (
        api(StubClient())
        .post("/v1/investigations", json={**REQUEST, "concepts": [{"label": "one"}]})
        .status_code
        == 400
    )


def test_upstream_failure_is_a_contract_problem_response():
    class Unavailable(StubClient):
        def submit(self, request):
            raise SciAgentsAdapterError("timeout", "Timed out.", retryable=True)

    response = api(Unavailable()).post("/v1/investigations", json=REQUEST)
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "sciagents_unavailable"


def test_poll_and_not_found_are_explicit():
    client = api(StubClient())
    known_id = "0b6f5a1e-3c2d-4e7f-9a8b-1c2d3e4f5a6b"
    assert client.get(f"/v1/investigations/{known_id}").json()["status"] == "running"
    missing = client.get("/v1/investigations/00000000-0000-4000-8000-000000000000")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/problem+json")


def test_portal_boundary_reaches_the_real_adapter_without_exposing_workflow_metadata():
    captured = {}

    def upstream(request):
        if request.method == "POST":
            captured["body"] = request.read().decode()
            return httpx.Response(202, json={"run_id": "run-d2", "status": "queued"})
        return httpx.Response(
            200,
            json={
                "proposal": {"hypothesis": "A fictional research lead."},
                "grounding": {"citations": []},
                "evaluation": {"passed_quality_gate": True},
                "error": None,
            },
        )

    http = httpx.Client(
        base_url="https://sciagents.invalid",
        transport=httpx.MockTransport(upstream),
    )
    boundary = api(SciAgentsClient("https://sciagents.invalid", http_client=http))
    queued = boundary.post("/v1/investigations", json=REQUEST)
    completed = boundary.get(queued.headers["location"])

    assert queued.status_code == 202
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert captured["body"] == (
        '{"keywords":["Metformin","Diabetes"],"mode":"sequential","human_review":false}'
    )
    assert "Question fictive" not in captured["body"]
    assert "proj-001" not in captured["body"]
