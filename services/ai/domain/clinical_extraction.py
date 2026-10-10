from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

MAX_SOURCE_LENGTH = 20000

EXTRACTION_NOTICE = (
    "Draft for clinician review. AI-assisted extraction is advisory and is not "
    "confirmed clinical data until an accountable clinician validates it."
)


class InvalidExtraction(ValueError):
    pass


class SourceType(StrEnum):
    TRANSCRIPT = "transcript"
    PHYSICIAN_NOTE = "physician_note"
    LAB_REPORT = "lab_report"


class ItemCategory(StrEnum):
    SYMPTOM = "symptom"
    OBSERVATION = "observation"
    MEASUREMENT = "measurement"
    MEDICATION = "medication"
    DIAGNOSIS_MENTIONED = "diagnosis_mentioned"
    FOLLOW_UP_ACTION = "follow_up_action"


class ExtractorKind(StrEnum):
    DETERMINISTIC_FIXTURE = "deterministic_fixture"
    MODEL = "model"


class ReviewStatus(StrEnum):
    PENDING_CLINICIAN_REVIEW = "pending_clinician_review"


@dataclass(frozen=True)
class ExtractionSource:
    type: SourceType
    text: str
    language: str | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise InvalidExtraction("Source text must not be empty.")
        if len(self.text) > MAX_SOURCE_LENGTH:
            raise InvalidExtraction(
                f"Source text exceeds {MAX_SOURCE_LENGTH} characters."
            )


@dataclass(frozen=True)
class Evidence:
    quote: str
    start: int
    end: int


@dataclass(frozen=True)
class ExtractedItem:
    item_id: str
    category: ItemCategory
    text: str
    evidence: Evidence
    value: float | None = None
    unit: str | None = None
    abnormal: bool | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class MissingInformation:
    topic: str
    prompt: str


@dataclass(frozen=True)
class ExtractorInfo:
    kind: ExtractorKind
    name: str
    version: str
    mocked: bool


@dataclass(frozen=True)
class Provenance:
    extractor: ExtractorInfo
    generated_at: datetime
    source_type: SourceType


@dataclass(frozen=True)
class ExtractionDraft:
    """Advisory output. It is always pending clinician review; AI Services never confirms it."""

    extraction_id: str
    patient_ref: str
    requested_by: str
    source: ExtractionSource
    items: tuple[ExtractedItem, ...]
    missing_information: tuple[MissingInformation, ...]
    provenance: Provenance
    encounter_ref: str | None = None
    review_status: ReviewStatus = ReviewStatus.PENDING_CLINICIAN_REVIEW
    notice: str = EXTRACTION_NOTICE

    def __post_init__(self) -> None:
        if self.review_status is not ReviewStatus.PENDING_CLINICIAN_REVIEW:
            raise InvalidExtraction("An extraction draft cannot be confirmed by AI.")
        for item in self.items:
            span = self.source.text[item.evidence.start : item.evidence.end]
            if item.evidence.start >= item.evidence.end or span != item.evidence.quote:
                raise InvalidExtraction(
                    f"Evidence for item {item.item_id} does not match the source text."
                )
            if item.confidence is not None and not 0 <= item.confidence <= 1:
                raise InvalidExtraction(
                    f"Confidence for item {item.item_id} is outside [0, 1]."
                )
