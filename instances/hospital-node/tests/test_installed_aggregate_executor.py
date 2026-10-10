from datetime import date

from adapters.outbound.installed_aggregate_executor import InstalledAggregateExecutor
from domain.research_execution import ResearchExecutionRequest, ResearchSubject
from tests.conftest import DEMO_NOW


class ResearchDataStub:
    node_ref = "node-hospital-a"
    organization_ref = "org-hospital-a"
    mocked = False

    def __init__(self, subjects):
        self.subjects = subjects

    def research_subjects(self):
        return self.subjects


def request(population=None, minimum=10, variables=None):
    return ResearchExecutionRequest(
        execution_id="job-001-exec-a",
        job_ref="job-001",
        project_ref="proj-001",
        target={
            "node_ref": "node-hospital-a",
            "organization_ref": "org-hospital-a",
        },
        submitted_by={
            "organization_ref": "org-platform",
            "actor_ref": "usr-aymen",
        },
        purpose="Aggregate cardiometabolic risk research",
        authorization={
            "decision_ref": "dec-rar-001",
            "authority_organization_ref": "org-governance",
            "valid_until": "2099-12-31T23:59:59+01:00",
            "approved_organization_refs": ["org-hospital-a"],
            "approved_variables": ["hba1c"],
        },
        data_scope={
            "population": population
            or {"encounter_from": "2024-01-01", "encounter_to": "2026-12-31"},
            "variables": variables or ["hba1c"],
        },
        algorithm={
            "language": "python",
            "artifact_ref": "notebook://nb-001/cell/nb-001-cell-2",
            "sha256": "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801",
            "entrypoint": "compute",
        },
        output_policy={
            "kind": "aggregate_table",
            "minimum_cell_size": minimum,
            "require_disclosure_review": True,
        },
    )


def subjects(count):
    return tuple(
        ResearchSubject(
            patient_ref=f"local-{index}",
            encounter_dates=(date(2026, 1, 1),),
            hba1c_values=(8.0 if index < count / 2 else 6.0,),
        )
        for index in range(count)
    )


def test_releases_only_aggregate_cells_when_minimum_is_met():
    result = InstalledAggregateExecutor(ResearchDataStub(subjects(10))).execute(
        request(), DEMO_NOW
    )
    assert result["outcome"] == "released"
    assert result["columns"] == ["participant_count", "hba1c_above_7_pct"]
    assert result["rows"] == [[10, 50.0]]
    assert "local-" not in str(result)


def test_suppresses_small_cells_and_returns_explicit_empty():
    executor = InstalledAggregateExecutor(ResearchDataStub(subjects(2)))
    suppressed = executor.execute(request(), DEMO_NOW)
    assert suppressed["outcome"] == "suppressed"
    assert suppressed["rows"] == []
    assert suppressed["disclosure"]["reason_code"] == "minimum_cell_size"

    empty = executor.execute(
        request(population={"encounter_from": "2030-01-01"}), DEMO_NOW
    )
    assert empty["outcome"] == "empty"
    assert empty["rows"] == []


def test_refuses_uninstalled_or_unsupported_work():
    executor = InstalledAggregateExecutor(ResearchDataStub(subjects(10)))
    unsupported = request(variables=["age_band"])
    try:
        executor.execute(unsupported, DEMO_NOW)
    except ValueError as error:
        assert "not installed" in str(error)
    else:
        raise AssertionError("unsupported variables must fail")
