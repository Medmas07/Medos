from application.research_orchestrator import ResearchOrchestrator
from domain.research_job import (
    AuthorizationDecision,
    ExecutionStatus,
    JobStatus,
    NodeExecution,
    ResearchJob,
)


class AuthorizationStub:
    def __init__(self, *, approved=True, unavailable=False, valid_until=None):
        self.approved = approved
        self.unavailable = unavailable
        self.valid_until = valid_until

    def check(self, job):
        if self.unavailable:
            raise ConnectionError
        return AuthorizationDecision(
            job.authorization_decision_ref,
            self.approved,
            job.target_organizations if self.approved else (),
            tuple(job.data_scope["variables"]) if self.approved else (),
            "org-governance",
            self.valid_until
            or ("2099-12-31T23:59:59+01:00" if self.approved else None),
            None if self.approved else "scope_denied",
        )


class ExecutionStub:
    def __init__(self, *, fail_organization=None, invalid_organization=None):
        self.fail_organization = fail_organization
        self.invalid_organization = invalid_organization
        self.submitted = []

    def submit(self, job, organization_ref, authorization):
        self.submitted.append(organization_ref)
        if organization_ref == self.fail_organization:
            raise ConnectionError
        return NodeExecution(
            f"{job.job_ref}-exec-{organization_ref}",
            organization_ref,
            ExecutionStatus.ACCEPTED,
        )

    def read(self, execution):
        source = (
            "org-wrong"
            if execution.organization_ref == self.invalid_organization
            else execution.organization_ref
        )
        return NodeExecution(
            execution.execution_id,
            execution.organization_ref,
            ExecutionStatus.COMPLETED,
            result={
                "outcome": "released",
                "columns": ["participant_count", "hba1c_above_7_pct"],
                "rows": [[42, 25.0]],
                "disclosure": {
                    "status": "passed",
                    "minimum_cell_size": 10,
                    "checked_at": "2026-10-10T12:00:01+00:00",
                },
                "provenance": {
                    "algorithm_sha256": "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801",
                    "authorization_decision_ref": "dec-rar-001",
                    "source_organization_ref": source,
                    "source_node_ref": execution.organization_ref.replace(
                        "org-", "node-", 1
                    ),
                    "executed_at": "2026-10-10T12:00:00+00:00",
                },
            },
        )


def job(job_ref="job-001"):
    return ResearchJob(
        job_ref=job_ref,
        project_ref="proj-001",
        authorization_decision_ref="dec-rar-001",
        requested_by="usr-aymen",
        purpose="Aggregate cardiometabolic risk research",
        target_organizations=("org-hospital-a", "org-hospital-b"),
        data_scope={"variables": ["age_band", "hba1c"]},
        algorithm={
            "language": "python",
            "artifact_ref": "notebook://nb-001/cell/nb-001-cell-2",
            "sha256": "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801",
            "entrypoint": "compute",
        },
        output_policy={
            "kind": "aggregate_table",
            "minimum_cell_size": 10,
            "require_disclosure_review": True,
        },
    )


def test_authorized_job_dispatches_and_aggregates_controlled_results():
    execution = ExecutionStub()
    orchestrator = ResearchOrchestrator(AuthorizationStub(), execution)

    submitted = orchestrator.submit(job())
    assert submitted.status is JobStatus.RUNNING
    assert execution.submitted == ["org-hospital-a", "org-hospital-b"]

    completed = orchestrator.read("job-001")
    assert completed.status is JobStatus.COMPLETED
    assert len(completed.executions) == 2
    assert all(item.result["outcome"] == "released" for item in completed.executions)
    assert completed.aggregation.status.value == "released"
    assert completed.aggregation.rows == ((84, 25.0),)
    assert completed.aggregation.included_organization_refs == (
        "org-hospital-a",
        "org-hospital-b",
    )
    assert all(
        item.output_validation.status.value == "passed" for item in completed.executions
    )


def test_denied_job_never_reaches_a_hospital_node():
    execution = ExecutionStub()
    orchestrator = ResearchOrchestrator(AuthorizationStub(approved=False), execution)
    denied = orchestrator.submit(job("job-denied"))
    assert denied.status is JobStatus.DENIED
    assert denied.error.code == "scope_denied"
    assert execution.submitted == []


def test_unavailable_governance_fails_closed_and_is_retryable():
    execution = ExecutionStub()
    orchestrator = ResearchOrchestrator(AuthorizationStub(unavailable=True), execution)
    failed = orchestrator.submit(job("job-governance-down"))
    assert failed.status is JobStatus.FAILED
    assert failed.error.code == "governance_unavailable"
    assert failed.error.retryable is True
    assert execution.submitted == []


def test_expired_authorization_never_reaches_a_hospital_node():
    execution = ExecutionStub()
    orchestrator = ResearchOrchestrator(
        AuthorizationStub(valid_until="2020-01-01T00:00:00+00:00"), execution
    )
    denied = orchestrator.submit(job("job-expired"))
    assert denied.status is JobStatus.DENIED
    assert denied.error.code == "authorization_expired"
    assert execution.submitted == []


def test_partial_node_failure_is_explicit_and_aggregation_is_unavailable():
    execution = ExecutionStub(fail_organization="org-hospital-b")
    orchestrator = ResearchOrchestrator(AuthorizationStub(), execution)
    running = orchestrator.submit(job("job-partial"))
    assert running.status is JobStatus.RUNNING
    failed = orchestrator.read("job-partial")
    assert failed.status is JobStatus.FAILED
    assert failed.error.code == "node_execution_failed"
    assert {item.status for item in failed.executions} == {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
    }
    assert failed.aggregation.status.value == "not_available"


def test_invalid_node_output_fails_closed_and_is_not_exposed():
    orchestrator = ResearchOrchestrator(
        AuthorizationStub(),
        ExecutionStub(invalid_organization="org-hospital-b"),
    )
    orchestrator.submit(job("job-invalid-output"))
    failed = orchestrator.read("job-invalid-output")
    assert failed.status is JobStatus.FAILED
    assert failed.error.code == "output_rejected"
    assert failed.aggregation.status.value == "not_available"
    accepted, rejected = failed.executions
    assert accepted.output_validation.status.value == "passed"
    assert accepted.result is not None
    assert rejected.output_validation.status.value == "rejected"
    assert rejected.output_validation.error.code == "output_provenance_invalid"
    assert rejected.result is None
