from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from domain.clinical_extraction import (
    ExtractedItem,
    ExtractionDraft,
    ExtractionSource,
    ExtractorInfo,
    MissingInformation,
    Provenance,
)


@dataclass(frozen=True)
class ExtractorOutput:
    items: tuple[ExtractedItem, ...]
    missing_information: tuple[MissingInformation, ...]
    # Who produced this output; with provider fallback it can differ from call to call.
    info: ExtractorInfo


class ExtractionUnavailable(Exception):
    """No extractor could produce a usable draft. Maps to 503 in the contract."""


class ClinicalExtractor(Protocol):
    """Port for whatever turns source text into items: fixtures or a model (HC-153)."""

    def extract(self, source: ExtractionSource) -> ExtractorOutput: ...


@dataclass(frozen=True)
class ExtractionRequest:
    patient_ref: str
    requested_by: str
    source: ExtractionSource
    encounter_ref: str | None = None


class ExtractClinicalInformation:
    def __init__(
        self,
        extractor: ClinicalExtractor,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._extractor = extractor
        self._clock = clock
        self._new_id = new_id

    def __call__(self, request: ExtractionRequest) -> ExtractionDraft:
        output = self._extractor.extract(request.source)
        return ExtractionDraft(
            extraction_id=self._new_id(),
            patient_ref=request.patient_ref,
            encounter_ref=request.encounter_ref,
            requested_by=request.requested_by,
            source=request.source,
            items=output.items,
            missing_information=output.missing_information,
            provenance=Provenance(
                extractor=output.info,
                generated_at=self._clock(),
                source_type=request.source.type,
            ),
        )
