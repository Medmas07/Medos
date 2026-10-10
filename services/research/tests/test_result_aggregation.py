from application.result_aggregation import ControlledResultAggregator
from domain.research_job import ExecutionStatus, NodeExecution, ResearchJob


SHA = "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801"


def job(*executions):
    return ResearchJob(
        job_ref="job-001",
        project_ref="proj-001",
        authorization_decision_ref="dec-rar-001",
        requested_by="usr-aymen",
        purpose="Aggregate cardiometabolic risk research",
        target_organizations=tuple(item.organization_ref for item in executions),
        data_scope={"variables": ["hba1c"]},
        algorithm={"sha256": SHA},
        output_policy={"minimum_cell_size": 10},
        executions=list(executions),
    )


def execution(organization, outcome, *, row=None, mocked=False):
    columns = ["participant_count", "hba1c_above_7_pct"] if row else []
    return NodeExecution(
        execution_id=f"exec-{organization}",
        organization_ref=organization,
        status=ExecutionStatus.COMPLETED,
        mocked=mocked,
        result={
            "outcome": outcome,
            "columns": columns,
            "rows": [row] if row else [],
            "disclosure": {
                "status": "suppressed" if outcome == "suppressed" else "passed",
                "minimum_cell_size": 10,
            },
            "provenance": {
                "algorithm_sha256": SHA,
                "authorization_decision_ref": "dec-rar-001",
                "source_organization_ref": organization,
            },
        },
    )


def test_weights_released_node_percentages_by_participant_count():
    result = ControlledResultAggregator().aggregate(
        job(
            execution("org-hospital-a", "released", row=[20, 10.0]),
            execution("org-hospital-b", "released", row=[30, 30.0], mocked=True),
        )
    )
    assert result.status.value == "released"
    assert result.rows == ((50, 22.0),)
    assert result.mocked is True


def test_suppressed_node_is_never_reconstructed_and_marks_partial_coverage():
    result = ControlledResultAggregator().aggregate(
        job(
            execution("org-hospital-a", "released", row=[20, 10.0]),
            execution("org-hospital-b", "suppressed"),
        )
    )
    assert result.status.value == "partial"
    assert result.rows == ((20, 10.0),)
    assert result.excluded_organization_refs == ("org-hospital-b",)
    assert result.disclosure["suppressed_organization_count"] == 1


def test_all_empty_and_all_suppressed_have_explicit_non_released_states():
    aggregator = ControlledResultAggregator()
    empty = aggregator.aggregate(job(execution("org-hospital-a", "empty")))
    suppressed = aggregator.aggregate(job(execution("org-hospital-a", "suppressed")))
    assert empty.status.value == "empty"
    assert empty.rows == ()
    assert suppressed.status.value == "suppressed"
    assert suppressed.rows == ()


def test_invalid_provenance_fails_closed():
    node = execution("org-hospital-a", "released", row=[20, 10.0])
    node.result["provenance"]["source_organization_ref"] = "org-hospital-b"
    result = ControlledResultAggregator().aggregate(job(node))
    assert result.status.value == "failed"
    assert result.error.code == "invalid_controlled_result"
