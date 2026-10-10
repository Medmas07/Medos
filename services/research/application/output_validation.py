"""D4 fail-closed validation before a Hospital Node output can be released."""

from datetime import datetime
from math import isfinite

from domain.research_job import (
    JobError,
    NodeExecution,
    OutputValidation,
    OutputValidationStatus,
    ResearchJob,
)


class ResearchOutputValidator:
    """Validate the one bounded HC-183 result; this is not a generic scanner."""

    COLUMNS = ["participant_count", "hba1c_above_7_pct"]
    RESULT_KEYS = {"outcome", "columns", "rows", "disclosure", "provenance"}
    DISCLOSURE_KEYS = {
        "status",
        "minimum_cell_size",
        "checked_at",
        "reason_code",
    }
    PROVENANCE_KEYS = {
        "algorithm_sha256",
        "authorization_decision_ref",
        "executed_at",
        "source_organization_ref",
        "source_node_ref",
    }

    def validate(self, execution: NodeExecution, job: ResearchJob) -> OutputValidation:
        checks: list[str] = []
        result = execution.result
        if not isinstance(result, dict) or set(result) != self.RESULT_KEYS:
            return self._rejected("output_schema_invalid", checks)
        checks.append("controlled_result_schema")

        outcome = result["outcome"]
        if outcome not in {"released", "empty", "suppressed"}:
            return self._rejected("output_schema_invalid", checks)
        disclosure = result["disclosure"]
        provenance = result["provenance"]
        if (
            not isinstance(disclosure, dict)
            or not set(disclosure) <= self.DISCLOSURE_KEYS
            or not {"status", "minimum_cell_size", "checked_at"} <= set(disclosure)
            or not isinstance(provenance, dict)
            or set(provenance) != self.PROVENANCE_KEYS
        ):
            return self._rejected("output_schema_invalid", checks)
        checks.append("metadata_schema")

        if not self._valid_disclosure(outcome, disclosure, job):
            return self._rejected("output_policy_failed", checks)
        checks.append("disclosure_policy")

        if not self._valid_provenance(provenance, execution, job):
            return self._rejected("output_provenance_invalid", checks)
        checks.append("provenance_binding")

        if not self._valid_timestamps(disclosure, provenance):
            return self._rejected("output_timestamp_invalid", checks)
        checks.append("timestamp_order")

        if not self._valid_cells(outcome, result, job):
            return self._rejected("output_cell_unsafe", checks)
        checks.extend(("bounded_columns", "minimum_cell_size"))
        return OutputValidation(OutputValidationStatus.PASSED, tuple(checks))

    @staticmethod
    def _rejected(code: str, checks: list[str]) -> OutputValidation:
        return OutputValidation(
            OutputValidationStatus.REJECTED,
            tuple(checks),
            JobError(
                code,
                "The Hospital Node output did not pass release validation.",
                False,
            ),
        )

    @staticmethod
    def _valid_disclosure(outcome: str, disclosure: dict, job: ResearchJob) -> bool:
        if (
            disclosure.get("minimum_cell_size")
            != job.output_policy["minimum_cell_size"]
        ):
            return False
        if outcome == "suppressed":
            return (
                disclosure.get("status") == "suppressed"
                and disclosure.get("reason_code") == "minimum_cell_size"
            )
        return disclosure.get("status") == "passed" and "reason_code" not in disclosure

    @staticmethod
    def _valid_provenance(
        provenance: dict, execution: NodeExecution, job: ResearchJob
    ) -> bool:
        expected_node = execution.organization_ref.replace("org-", "node-", 1)
        return (
            provenance.get("algorithm_sha256") == job.algorithm["sha256"]
            and provenance.get("authorization_decision_ref")
            == job.authorization_decision_ref
            and provenance.get("source_organization_ref") == execution.organization_ref
            and provenance.get("source_node_ref") == expected_node
        )

    @staticmethod
    def _valid_timestamps(disclosure: dict, provenance: dict) -> bool:
        try:
            executed_at = datetime.fromisoformat(provenance["executed_at"])
            checked_at = datetime.fromisoformat(disclosure["checked_at"])
        except (TypeError, ValueError):
            return False
        return (
            executed_at.tzinfo is not None
            and checked_at.tzinfo is not None
            and checked_at >= executed_at
        )

    def _valid_cells(self, outcome: str, result: dict, job: ResearchJob) -> bool:
        columns = result["columns"]
        rows = result["rows"]
        if outcome in {"empty", "suppressed"}:
            return columns == [] and rows == []
        if columns != self.COLUMNS or not isinstance(rows, list) or len(rows) != 1:
            return False
        row = rows[0]
        if not isinstance(row, list) or len(row) != 2:
            return False
        count, percentage = row
        minimum = job.output_policy["minimum_cell_size"]
        return (
            isinstance(count, int)
            and not isinstance(count, bool)
            and count >= minimum
            and isinstance(percentage, (int, float))
            and not isinstance(percentage, bool)
            and isfinite(percentage)
            and 0 <= percentage <= 100
        )
