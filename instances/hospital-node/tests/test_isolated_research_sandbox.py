import json
import subprocess

from adapters.outbound.isolated_research_sandbox import IsolatedResearchSandbox
from application.research_execution_agent import LocalExecutionError
from tests.conftest import DEMO_NOW
from tests.test_installed_aggregate_executor import ResearchDataStub, request, subjects


def test_runs_installed_aggregate_in_isolated_process_without_patient_refs():
    result = IsolatedResearchSandbox(ResearchDataStub(subjects(10))).execute(
        request(), DEMO_NOW
    )
    assert result["outcome"] == "released"
    assert result["rows"] == [[10, 50.0]]
    assert "local-" not in str(result)
    assert result["sandbox"] == {
        "mode": "isolated_process",
        "python_isolated": True,
        "site_packages_disabled": True,
        "environment_cleared": True,
        "network": "denied",
        "filesystem": "denied_after_startup",
        "wall_time_seconds": 2.0,
        "max_input_bytes": 262144,
        "max_output_bytes": 65536,
        "os_resource_limits": result["sandbox"]["os_resource_limits"],
    }
    assert result["sandbox"]["os_resource_limits"] in {
        "posix_rlimit",
        "parent_enforced",
    }


def test_keeps_empty_and_suppressed_states_inside_sandbox():
    sandbox = IsolatedResearchSandbox(ResearchDataStub(subjects(2)))
    assert sandbox.execute(request(), DEMO_NOW)["outcome"] == "suppressed"
    assert (
        sandbox.execute(request(population={"encounter_from": "2030-01-01"}), DEMO_NOW)[
            "outcome"
        ]
        == "empty"
    )


def test_package_allowlist_denies_uninstalled_work_before_process_start():
    sandbox = IsolatedResearchSandbox(ResearchDataStub(subjects(10)))
    try:
        sandbox.execute(request(variables=["age_band"]), DEMO_NOW)
    except LocalExecutionError as error:
        assert error.code == "package_policy_denied"
    else:
        raise AssertionError("uninstalled work must be denied")


def test_process_boundary_clears_environment_and_excludes_patient_refs(monkeypatch):
    captured = {}

    def run(command, **kwargs):
        captured.update(command=command, **kwargs)
        output = {
            "outcome": "released",
            "columns": ["participant_count", "hba1c_above_7_pct"],
            "rows": [[10, 50.0]],
            "reason_code": None,
            "resource_mode": "parent_enforced",
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(output).encode(), b"")

    monkeypatch.setattr(subprocess, "run", run)
    IsolatedResearchSandbox(ResearchDataStub(subjects(10))).execute(request(), DEMO_NOW)
    assert captured["command"][1:3] == ["-I", "-S"]
    assert captured["env"] == {}
    assert captured["timeout"] == 2.0
    assert b"local-" not in captured["input"]
    assert captured["cwd"]


def test_timeout_has_explicit_non_retryable_state(monkeypatch):
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    try:
        IsolatedResearchSandbox(ResearchDataStub(subjects(10))).execute(
            request(), DEMO_NOW
        )
    except LocalExecutionError as error:
        assert error.code == "sandbox_timeout"
        assert error.retryable is False
    else:
        raise AssertionError("sandbox timeout must fail")
