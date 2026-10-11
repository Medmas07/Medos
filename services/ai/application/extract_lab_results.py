"""Extract structured lab results from a lab report (HC-155): use case and port."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from domain.lab_extraction import (
    ExtractorInfo,
    LabExtractionDraft,
    ProposedResult,
    verified,
)


@dataclass(frozen=True)
class LabExtractorOutput:
    proposals: tuple[ProposedResult, ...]
    extractor: ExtractorInfo
    uncertainty_notes: tuple[str, ...] = ()
    # Rows the extractor returned that were not even well formed.
    malformed: int = 0


class LabExtractionUnavailable(Exception):
    """No extractor could produce a usable draft. Maps to 503 in the contract."""


class LabExtractor(Protocol):
    """Whatever proposes lab results from a report: fixtures or a model."""

    def extract(self, report: str) -> LabExtractorOutput: ...


@dataclass(frozen=True)
class LabExtractionRequest:
    patient_ref: str
    requested_by: str
    report: str
    encounter_ref: str | None = None


class ExtractLabResults:
    """Every proposal is verified against the report and flagged here, whatever the
    extractor: the flag is never the extractor's."""

    def __init__(
        self,
        extractor: LabExtractor,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._extractor = extractor
        self._clock = clock
        self._new_id = new_id

    def __call__(self, request: LabExtractionRequest) -> LabExtractionDraft:
        output = self._extractor.extract(request.report)
        results = []
        for proposal in output.proposals:
            result = verified(proposal, request.report, f"result-{len(results) + 1}")
            if result is not None:
                results.append(result)
        return LabExtractionDraft(
            extraction_id=self._new_id(),
            patient_ref=request.patient_ref,
            requested_by=request.requested_by,
            encounter_ref=request.encounter_ref,
            results=tuple(results),
            unverified_results_dropped=output.malformed
            + len(output.proposals)
            - len(results),
            extractor=output.extractor,
            generated_at=self._clock(),
            uncertainty_notes=output.uncertainty_notes,
        )
