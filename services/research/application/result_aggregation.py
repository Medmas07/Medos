"""Fail-closed aggregation of the bounded HC-183 controlled result."""

from domain.research_job import (
    AggregationStatus,
    ControlledAggregation,
    JobError,
    NodeExecution,
    ResearchJob,
)


class ControlledResultError(ValueError):
    """A node result is unsafe or incompatible with this bounded aggregator."""


class ControlledResultAggregator:
    COLUMNS = ("participant_count", "hba1c_above_7_pct")

    def aggregate(self, job: ResearchJob) -> ControlledAggregation:
        released: list[tuple[NodeExecution, int, float]] = []
        empty: list[str] = []
        suppressed: list[str] = []

        try:
            for execution in job.executions:
                outcome = self._validate(execution, job)
                if outcome == "empty":
                    empty.append(execution.organization_ref)
                elif outcome == "suppressed":
                    suppressed.append(execution.organization_ref)
                else:
                    count, percentage = execution.result["rows"][0]
                    released.append((execution, count, percentage))
        except (KeyError, TypeError, ControlledResultError):
            return ControlledAggregation(
                status=AggregationStatus.FAILED,
                mocked=any(item.mocked for item in job.executions),
                error=JobError(
                    "invalid_controlled_result",
                    "A Hospital Node result could not be safely aggregated.",
                    False,
                ),
            )

        mocked = any(item.mocked for item in job.executions)
        excluded = tuple(suppressed)
        provenance = {
            "algorithm_sha256": job.algorithm["sha256"],
            "authorization_decision_ref": job.authorization_decision_ref,
            "source_organization_refs": [
                item.organization_ref for item, _, _ in released
            ],
            "excluded_organization_refs": [*suppressed],
        }
        disclosure = {
            "status": "partial" if suppressed and released else "passed",
            "minimum_cell_size": job.output_policy["minimum_cell_size"],
            "suppressed_organization_count": len(suppressed),
        }

        if not released:
            status = (
                AggregationStatus.SUPPRESSED if suppressed else AggregationStatus.EMPTY
            )
            return ControlledAggregation(
                status=status,
                excluded_organization_refs=excluded,
                disclosure=disclosure,
                provenance=provenance,
                mocked=mocked,
            )

        total = sum(count for _, count, _ in released)
        percentage = round(
            sum(count * value for _, count, value in released) / total, 1
        )
        return ControlledAggregation(
            status=(
                AggregationStatus.PARTIAL if suppressed else AggregationStatus.RELEASED
            ),
            columns=self.COLUMNS,
            rows=((total, percentage),),
            included_organization_refs=tuple(
                item.organization_ref for item, _, _ in released
            ),
            excluded_organization_refs=excluded,
            disclosure=disclosure,
            provenance=provenance,
            mocked=mocked,
        )

    def _validate(self, execution: NodeExecution, job: ResearchJob) -> str:
        result = execution.result
        if not isinstance(result, dict):
            raise ControlledResultError
        outcome = result.get("outcome")
        if outcome not in {"released", "empty", "suppressed"}:
            raise ControlledResultError

        disclosure = result.get("disclosure")
        provenance = result.get("provenance")
        if not isinstance(disclosure, dict) or not isinstance(provenance, dict):
            raise ControlledResultError
        if (
            disclosure.get("minimum_cell_size")
            != job.output_policy["minimum_cell_size"]
        ):
            raise ControlledResultError
        if provenance.get("algorithm_sha256") != job.algorithm["sha256"]:
            raise ControlledResultError
        if (
            provenance.get("authorization_decision_ref")
            != job.authorization_decision_ref
            or provenance.get("source_organization_ref") != execution.organization_ref
        ):
            raise ControlledResultError

        columns = result.get("columns")
        rows = result.get("rows")
        if outcome in {"empty", "suppressed"}:
            if rows != []:
                raise ControlledResultError
            if outcome == "suppressed" and (
                columns != [] or disclosure.get("status") != "suppressed"
            ):
                raise ControlledResultError
            if outcome == "empty" and disclosure.get("status") != "passed":
                raise ControlledResultError
            return outcome

        if columns != list(self.COLUMNS) or disclosure.get("status") != "passed":
            raise ControlledResultError
        if not isinstance(rows, list) or len(rows) != 1 or len(rows[0]) != 2:
            raise ControlledResultError
        count, percentage = rows[0]
        minimum = job.output_policy["minimum_cell_size"]
        if (
            not isinstance(count, int)
            or isinstance(count, bool)
            or count < minimum
            or not isinstance(percentage, (int, float))
            or isinstance(percentage, bool)
            or not 0 <= percentage <= 100
        ):
            raise ControlledResultError
        return outcome
