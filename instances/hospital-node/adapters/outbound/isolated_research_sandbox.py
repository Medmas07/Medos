"""D4 process-isolation adapter for the bounded installed aggregate."""

import json
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

from application.research_data import ResearchDataSource
from application.research_execution_agent import LocalExecutionError
from domain.research_execution import ResearchExecutionRequest

SUPPORTED_ALGORITHM_SHA256 = (
    "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801"
)
MAX_SUBJECTS = 10_000
MAX_VALUES = 100_000
MAX_OUTPUT_BYTES = 65_536
WALL_TIME_SECONDS = 2.0


class IsolatedResearchSandbox:
    def __init__(self, data: ResearchDataSource) -> None:
        self.data = data
        self.mocked = data.mocked
        self.worker = Path(__file__).with_name("sandbox_worker.py").resolve()

    def execute(self, request: ResearchExecutionRequest, now: datetime) -> dict:
        self._check_package_policy(request)
        subjects = self._bounded_subjects(request)
        payload = json.dumps(
            {
                "minimum_cell_size": request.output_policy["minimum_cell_size"],
                "subjects": subjects,
            },
            separators=(",", ":"),
        ).encode()
        if len(payload) > 262_144:
            raise LocalExecutionError(
                "sandbox_resource_exceeded", "Sandbox input quota was exceeded."
            )
        command = [sys.executable, "-I", "-S", str(self.worker)]
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            with tempfile.TemporaryDirectory(prefix="hc186-") as workdir:
                completed = subprocess.run(
                    command,
                    input=payload,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=workdir,
                    env={},
                    timeout=WALL_TIME_SECONDS,
                    check=False,
                    creationflags=flags,
                )
        except subprocess.TimeoutExpired as error:
            raise LocalExecutionError(
                "sandbox_timeout", "Sandbox wall-time limit was exceeded."
            ) from error
        if completed.returncode != 0 or len(completed.stdout) > MAX_OUTPUT_BYTES:
            raise LocalExecutionError(
                "sandbox_violation", "Sandbox execution was stopped by policy."
            )
        try:
            result = json.loads(completed.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LocalExecutionError(
                "sandbox_invalid_output", "Sandbox returned an invalid result."
            ) from error
        if (
            not isinstance(result, dict)
            or set(result)
            != {"outcome", "columns", "rows", "reason_code", "resource_mode"}
            or result["outcome"] not in {"released", "empty", "suppressed"}
            or not isinstance(result["columns"], list)
            or not isinstance(result["rows"], list)
            or result["resource_mode"] not in {"posix_rlimit", "parent_enforced"}
        ):
            raise LocalExecutionError(
                "sandbox_invalid_output", "Sandbox returned an invalid result."
            )
        return self._controlled_result(request, now, result)

    @staticmethod
    def _check_package_policy(request: ResearchExecutionRequest) -> None:
        algorithm = request.algorithm
        if (
            algorithm["language"] != "python"
            or algorithm["sha256"] != SUPPORTED_ALGORITHM_SHA256
            or algorithm["entrypoint"] != "compute"
            or not set(request.data_scope["variables"]) <= {"hba1c"}
        ):
            raise LocalExecutionError(
                "package_policy_denied", "The requested package is not installed."
            )

    def _bounded_subjects(self, request: ResearchExecutionRequest) -> list[dict]:
        population = request.data_scope["population"]
        if (
            population.get("age_min") is not None
            or population.get("age_max") is not None
        ):
            raise LocalExecutionError(
                "unsupported_population", "Local demographic data is unavailable."
            )
        start = _date(population.get("encounter_from"), date.min)
        end = _date(population.get("encounter_to"), date.max)
        subjects = [
            {"hba1c_values": list(subject.hba1c_values)}
            for subject in self.data.research_subjects()
            if any(start <= day <= end for day in subject.encounter_dates)
        ]
        if (
            len(subjects) > MAX_SUBJECTS
            or sum(len(subject["hba1c_values"]) for subject in subjects) > MAX_VALUES
        ):
            raise LocalExecutionError(
                "sandbox_resource_exceeded", "Sandbox record quota was exceeded."
            )
        return subjects

    def _controlled_result(
        self, request: ResearchExecutionRequest, now: datetime, worker: dict
    ) -> dict:
        outcome = worker["outcome"]
        disclosure = {
            "status": "suppressed" if outcome == "suppressed" else "passed",
            "minimum_cell_size": request.output_policy["minimum_cell_size"],
            "checked_at": now.isoformat(),
        }
        if worker.get("reason_code"):
            disclosure["reason_code"] = worker["reason_code"]
        return {
            "outcome": outcome,
            "columns": worker["columns"],
            "rows": worker["rows"],
            "disclosure": disclosure,
            "provenance": {
                "algorithm_sha256": request.algorithm["sha256"],
                "authorization_decision_ref": request.authorization["decision_ref"],
                "executed_at": now.isoformat(),
                "source_organization_ref": self.data.organization_ref,
                "source_node_ref": self.data.node_ref,
            },
            "sandbox": {
                "mode": "isolated_process",
                "python_isolated": True,
                "site_packages_disabled": True,
                "environment_cleared": True,
                "network": "denied",
                "filesystem": "denied_after_startup",
                "wall_time_seconds": WALL_TIME_SECONDS,
                "max_input_bytes": 262_144,
                "max_output_bytes": MAX_OUTPUT_BYTES,
                "os_resource_limits": worker["resource_mode"],
            },
        }


def _date(value: str | None, default: date) -> date:
    return date.fromisoformat(value) if value else default
