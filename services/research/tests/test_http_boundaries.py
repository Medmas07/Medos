from adapters.outbound import http_boundaries
from adapters.outbound.http_boundaries import (
    HttpGovernanceAuthorization,
    HttpHospitalExecution,
)
from domain.research_job import AuthorizationDecision, ExecutionStatus
from tests.test_research_orchestrator import job


class ResponseStub:
    def __init__(self, document):
        self.document = document

    def raise_for_status(self):
        return None

    def json(self):
        return self.document


def test_governance_adapter_maps_owned_authorization(monkeypatch):
    captured = {}

    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return ResponseStub(
            {
                "decision_ref": "dec-rar-001",
                "status": "approved",
                "approved_organization_refs": [
                    "org-hospital-a",
                    "org-hospital-b",
                ],
                "approved_variables": ["age_band", "hba1c"],
                "authority_organization_ref": "org-governance",
                "valid_until": "2026-12-31T23:59:59+01:00",
            }
        )

    monkeypatch.setattr(http_boundaries.httpx, "post", post)
    decision = HttpGovernanceAuthorization("http://governance:8200").check(job())
    assert decision.approved is True
    assert decision.valid_until == "2026-12-31T23:59:59+01:00"
    assert captured["json"]["data_scope"]["variables"] == ["age_band", "hba1c"]


def test_hospital_adapter_forwards_governance_scope_without_inventing_it(monkeypatch):
    captured = {}

    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return ResponseStub(
            {
                "execution_id": "job-001-exec-org-hospital-a",
                "job_ref": "job-001",
                "node_ref": "node-hospital-a",
                "status": "accepted",
                "accepted_at": "2026-10-10T12:00:00+01:00",
                "mocked": False,
            }
        )

    monkeypatch.setattr(http_boundaries.httpx, "post", post)
    authorization = AuthorizationDecision(
        "dec-rar-001",
        True,
        ("org-hospital-a",),
        ("age_band", "hba1c"),
        "org-governance",
        "2026-12-31T23:59:59+01:00",
    )
    execution = HttpHospitalExecution(
        {"org-hospital-a": "http://hospital-a:8101"}
    ).submit(job(), "org-hospital-a", authorization)
    assert execution.status is ExecutionStatus.ACCEPTED
    forwarded = captured["json"]["authorization"]
    assert forwarded["decision_ref"] == authorization.decision_ref
    assert forwarded["approved_organization_refs"] == ["org-hospital-a"]
    assert forwarded["valid_until"] == authorization.valid_until
