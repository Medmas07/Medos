"""Bounded installed aggregate for HC-183; never executes submitted source code."""

from datetime import date, datetime

from application.research_data import ResearchDataSource
from domain.research_execution import ResearchExecutionRequest

SUPPORTED_ALGORITHM_SHA256 = (
    "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801"
)


class InstalledAggregateExecutor:
    def __init__(self, data: ResearchDataSource) -> None:
        self.data = data
        self.mocked = data.mocked

    def execute(self, request: ResearchExecutionRequest, now: datetime) -> dict:
        algorithm = request.algorithm
        if (
            algorithm["language"] != "python"
            or algorithm["sha256"] != SUPPORTED_ALGORITHM_SHA256
            or algorithm["entrypoint"] != "compute"
            or not set(request.data_scope["variables"]) <= {"hba1c"}
        ):
            raise ValueError("algorithm is not installed")

        population = request.data_scope["population"]
        if (
            population.get("age_min") is not None
            or population.get("age_max") is not None
        ):
            raise ValueError("local demographic data is not available")
        encounter_from = _date(population.get("encounter_from"), date.min)
        encounter_to = _date(population.get("encounter_to"), date.max)
        subjects = tuple(
            subject
            for subject in self.data.research_subjects()
            if any(
                encounter_from <= day <= encounter_to for day in subject.encounter_dates
            )
        )
        if not subjects:
            return self._result(request, now, "empty", [], [])

        minimum = request.output_policy["minimum_cell_size"]
        if len(subjects) < minimum:
            return self._result(
                request,
                now,
                "suppressed",
                [],
                [],
                reason_code="minimum_cell_size",
            )

        values = [value for subject in subjects for value in subject.hba1c_values]
        if not values:
            return self._result(request, now, "empty", [], [])
        above_seven = round(100 * sum(value > 7 for value in values) / len(values), 1)
        return self._result(
            request,
            now,
            "released",
            ["participant_count", "hba1c_above_7_pct"],
            [[len(subjects), above_seven]],
        )

    def _result(
        self,
        request: ResearchExecutionRequest,
        now: datetime,
        outcome: str,
        columns: list[str],
        rows: list[list],
        reason_code: str | None = None,
    ) -> dict:
        disclosure = {
            "status": "suppressed" if outcome == "suppressed" else "passed",
            "minimum_cell_size": request.output_policy["minimum_cell_size"],
            "checked_at": now.isoformat(),
        }
        if reason_code:
            disclosure["reason_code"] = reason_code
        return {
            "outcome": outcome,
            "columns": columns,
            "rows": rows,
            "disclosure": disclosure,
            "provenance": {
                "algorithm_sha256": request.algorithm["sha256"],
                "authorization_decision_ref": request.authorization["decision_ref"],
                "executed_at": now.isoformat(),
                "source_organization_ref": self.data.organization_ref,
                "source_node_ref": self.data.node_ref,
            },
        }


def _date(value: str | None, default: date) -> date:
    return date.fromisoformat(value) if value else default
