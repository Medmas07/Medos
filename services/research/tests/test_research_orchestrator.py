from application.research_orchestrator import ResearchOrchestrator
from domain.research_job import JobStatus, StageStatus


def make_orchestrator():
    return ResearchOrchestrator()


def test_distributed_job_progresses_through_mocked_nodes_to_controlled_result():
    orchestrator = make_orchestrator()
    submitted = orchestrator.submit(
        job_ref="job-001",
        project_ref="proj-001",
        authorization_decision_ref="dec-rar-001",
        requested_by="usr-aymen",
        target_organizations=["org-hospital-a", "org-hospital-b"],
    )
    assert submitted.status is JobStatus.QUEUED

    running = orchestrator.read("job-001")
    assert running.status is JobStatus.RUNNING
    assert [stage.progress for stage in running.stages[1:3]] == [45, 45]

    completed = orchestrator.read("job-001")
    assert completed.status is JobStatus.COMPLETED
    assert completed.result["outcome"] == "released"
    assert all(stage.status is StageStatus.COMPLETED for stage in completed.stages)


def test_denied_authorization_never_runs_a_node():
    orchestrator = make_orchestrator()
    denied = orchestrator.submit(
        job_ref="job-denied",
        project_ref="proj-001",
        authorization_decision_ref="dec-unknown",
        requested_by="usr-aymen",
        target_organizations=["org-hospital-a", "org-hospital-b"],
    )
    assert denied.status is JobStatus.DENIED
    assert denied.error["code"] == "authorization_denied"
    assert all(stage.status is StageStatus.DENIED for stage in denied.stages)


def test_empty_and_failed_outcomes_are_explicit():
    orchestrator = make_orchestrator()
    orchestrator.submit(
        job_ref="job-empty",
        project_ref="proj-001",
        authorization_decision_ref="dec-rar-001",
        requested_by="usr-aymen",
        target_organizations=["org-hospital-a", "org-hospital-b"],
    )
    assert orchestrator.read("job-empty").status is JobStatus.RUNNING
    empty = orchestrator.read("job-empty")
    assert empty.result["outcome"] == "empty"
    orchestrator.submit(
        job_ref="job-failed",
        project_ref="proj-001",
        authorization_decision_ref="dec-rar-001",
        requested_by="usr-aymen",
        target_organizations=["org-hospital-a", "org-hospital-b"],
    )
    orchestrator.read("job-failed")
    failed = orchestrator.read("job-failed")
    assert failed.status is JobStatus.FAILED
    assert failed.error["retryable"] is True
