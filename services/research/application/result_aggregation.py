"""Fail-closed aggregation of the bounded HC-183 controlled result."""

from domain.research_job import (
    AggregationStatus,
    ControlledAggregation,
    JobError,
    NodeExecution,
    OutputValidationStatus,
    ResearchJob,
)


class ControlledResultAggregator:
    COLUMNS = ("participant_count", "hba1c_above_7_pct")

    def aggregate(self, job: ResearchJob) -> ControlledAggregation:
        released: list[tuple[NodeExecution, int, float]] = []
        empty: list[str] = []
        suppressed: list[str] = []

        try:
            for execution in job.executions:
                if (
                    execution.output_validation.status
                    is not OutputValidationStatus.PASSED
                    or execution.result is None
                ):
                    raise ValueError("output has not passed release validation")
                outcome = execution.result["outcome"]
                if outcome == "empty":
                    empty.append(execution.organization_ref)
                elif outcome == "suppressed":
                    suppressed.append(execution.organization_ref)
                else:
                    count, percentage = execution.result["rows"][0]
                    released.append((execution, count, percentage))
        except (KeyError, TypeError, ValueError):
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
