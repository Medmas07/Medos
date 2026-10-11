"""Structured laboratory results extracted from a lab report's text (HC-155).

A draft for clinician review, in the shape the Hospital Node keeps lab results
(domain/clinical_record.py there; `lab_reports` in hospital-node-federation.v1.yaml):
test, numeric value, unit, the reference range printed with it, and a flag.

Two rules keep the language model out of the safety decision:

- Verified against the text. A result is kept only if its quote is found in the report
  and its value appears in that quote; a reference range only if both bounds do.
- The flag is computed, not proposed. `low`, `normal`, or `high` comes from comparing
  the value with the range printed in the report, here, deterministically. Without a
  printed range there is no flag: no population range is ever assumed.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

MAX_REPORT_LENGTH = 20_000
# A number as printed in a report: digits, with a decimal point or comma.
_NUMBER = re.compile(r"(?<![\d.,])\d+(?:[.,]\d+)?(?![\d])")


class InvalidLabExtraction(ValueError):
    pass


class LabFlag(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class FlagBasis(Enum):
    # Computed from the reference range printed with the result.
    REFERENCE_RANGE = "reference_range"
    # No range printed with the result: no flag is given.
    NO_REFERENCE_RANGE = "no_reference_range"


class ExtractorKind(Enum):
    MODEL = "model"
    DETERMINISTIC_FIXTURE = "deterministic_fixture"


class ReviewStatus(Enum):
    PENDING_CLINICIAN_REVIEW = "pending_clinician_review"


@dataclass(frozen=True)
class Evidence:
    quote: str
    start: int
    end: int


@dataclass(frozen=True)
class ReferenceRange:
    low: float
    high: float

    def __post_init__(self) -> None:
        if self.low > self.high:
            raise InvalidLabExtraction(
                "a reference range's low bound exceeds its high one"
            )


@dataclass(frozen=True)
class ProposedResult:
    """What an extractor proposes; unverified."""

    test: str
    value: float
    unit: str
    quote: str
    reference_range: ReferenceRange | None = None


@dataclass(frozen=True)
class LabResult:
    result_id: str
    test: str
    value: float
    unit: str
    reference_range: ReferenceRange | None
    flag: LabFlag | None
    flag_basis: FlagBasis
    evidence: Evidence


@dataclass(frozen=True)
class ExtractorInfo:
    kind: ExtractorKind
    name: str
    version: str
    mocked: bool


@dataclass(frozen=True)
class LabExtractionDraft:
    extraction_id: str
    patient_ref: str
    requested_by: str
    encounter_ref: str | None
    results: tuple[LabResult, ...]
    # Proposed results that failed verification and are not shown.
    unverified_results_dropped: int
    extractor: ExtractorInfo
    generated_at: datetime
    uncertainty_notes: tuple[str, ...] = ()
    advisory: bool = True
    review_status: ReviewStatus = ReviewStatus.PENDING_CLINICIAN_REVIEW


def flag_for(value: float, reference_range: ReferenceRange | None) -> LabFlag | None:
    """Deterministic: below the range is low, above it high, inside it normal."""
    if reference_range is None:
        return None
    if value < reference_range.low:
        return LabFlag.LOW
    if value > reference_range.high:
        return LabFlag.HIGH
    return LabFlag.NORMAL


def numbers_in(text: str) -> list[float]:
    """The numbers printed in `text`, reading a decimal comma as a point."""
    return [float(n.replace(",", ".")) for n in _NUMBER.findall(text)]


def locate(quote: str, text: str) -> Evidence | None:
    """The quote's position in the report, exactly or ignoring case only, keeping the
    report's own characters."""
    quote = quote.strip()
    if not quote:
        return None
    start = text.find(quote)
    if start < 0:
        start = text.lower().find(quote.lower())
    if start < 0:
        return None
    return Evidence(text[start : start + len(quote)], start, start + len(quote))


def verified(proposal: ProposedResult, report: str, result_id: str) -> LabResult | None:
    """The result as the report supports it, flagged here; None if it is not supported.

    The quote must be in the report and contain the value. A range is kept only if both
    bounds are in the quote too; otherwise the result has no range and no flag."""
    if not proposal.test.strip() or not proposal.unit.strip():
        return None
    evidence = locate(proposal.quote, report)
    if evidence is None:
        return None
    printed = numbers_in(evidence.quote)
    if proposal.value not in printed:
        return None
    reference_range = proposal.reference_range
    if reference_range is not None and not (
        reference_range.low in printed and reference_range.high in printed
    ):
        reference_range = None
    flag = flag_for(proposal.value, reference_range)
    return LabResult(
        result_id=result_id,
        test=proposal.test.strip(),
        value=proposal.value,
        unit=proposal.unit.strip(),
        reference_range=reference_range,
        flag=flag,
        flag_basis=FlagBasis.REFERENCE_RANGE
        if reference_range is not None
        else FlagBasis.NO_REFERENCE_RANGE,
        evidence=evidence,
    )
