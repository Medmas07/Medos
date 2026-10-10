from application.output_validation import ResearchOutputValidator
from domain.research_job import ExecutionStatus, NodeExecution
from tests.test_research_orchestrator import job


SHA = "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801"


def execution(outcome="released"):
    suppressed = outcome == "suppressed"
    result = {
        "outcome": outcome,
        "columns": (
            [] if outcome != "released" else ["participant_count", "hba1c_above_7_pct"]
        ),
        "rows": [] if outcome != "released" else [[20, 25.0]],
        "disclosure": {
            "status": "suppressed" if suppressed else "passed",
            "minimum_cell_size": 10,
            "checked_at": "2026-10-10T12:00:01+00:00",
        },
        "provenance": {
            "algorithm_sha256": SHA,
            "authorization_decision_ref": "dec-rar-001",
            "executed_at": "2026-10-10T12:00:00+00:00",
            "source_organization_ref": "org-hospital-a",
            "source_node_ref": "node-hospital-a",
        },
    }
    if suppressed:
        result["disclosure"]["reason_code"] = "minimum_cell_size"
    return NodeExecution(
        "exec-a",
        "org-hospital-a",
        ExecutionStatus.COMPLETED,
        result=result,
        mocked=True,
    )


def validate(node):
    return ResearchOutputValidator().validate(node, job())


def test_released_empty_and_suppressed_outputs_pass_bounded_validation():
    for outcome in ("released", "empty", "suppressed"):
        result = validate(execution(outcome))
        assert result.status.value == "passed"
        assert result.error is None
        assert result.checks == (
            "controlled_result_schema",
            "metadata_schema",
            "disclosure_policy",
            "provenance_binding",
            "timestamp_order",
            "bounded_columns",
            "minimum_cell_size",
        )


def test_unexpected_patient_level_field_is_rejected():
    node = execution()
    node.result["patient_refs"] = ["pat-a"]
    result = validate(node)
    assert result.status.value == "rejected"
    assert result.error.code == "output_schema_invalid"


def test_small_released_cell_is_rejected_even_if_node_marks_it_passed():
    node = execution()
    node.result["rows"] = [[9, 25.0]]
    result = validate(node)
    assert result.status.value == "rejected"
    assert result.error.code == "output_cell_unsafe"


def test_mismatched_provenance_is_rejected():
    node = execution()
    node.result["provenance"]["authorization_decision_ref"] = "dec-other"
    result = validate(node)
    assert result.status.value == "rejected"
    assert result.error.code == "output_provenance_invalid"


def test_missing_timezone_or_review_before_execution_is_rejected():
    missing_timezone = execution()
    missing_timezone.result["provenance"]["executed_at"] = "2026-10-10T12:00:00"
    assert validate(missing_timezone).error.code == "output_timestamp_invalid"

    reversed_order = execution()
    reversed_order.result["disclosure"]["checked_at"] = "2026-10-10T11:59:59+00:00"
    assert validate(reversed_order).error.code == "output_timestamp_invalid"
