from dataclasses import replace
from datetime import UTC, datetime

import pytest

from domain.clinical_extraction import (
    MAX_SOURCE_LENGTH,
    Evidence,
    ExtractedItem,
    ExtractionDraft,
    ExtractionSource,
    ExtractorInfo,
    ExtractorKind,
    InvalidExtraction,
    ItemCategory,
    Provenance,
    ReviewStatus,
    SourceType,
)

SOURCE = ExtractionSource(
    type=SourceType.PHYSICIAN_NOTE, text="Mild cough since Monday."
)
PROVENANCE = Provenance(
    extractor=ExtractorInfo(
        ExtractorKind.DETERMINISTIC_FIXTURE, "test", "1", mocked=True
    ),
    generated_at=datetime(2026, 10, 10, tzinfo=UTC),
    source_type=SourceType.PHYSICIAN_NOTE,
)
COUGH = ExtractedItem(
    item_id="i1",
    category=ItemCategory.SYMPTOM,
    text="Mild cough",
    evidence=Evidence(quote="Mild cough", start=0, end=10),
)


def draft(*items: ExtractedItem) -> ExtractionDraft:
    return ExtractionDraft(
        extraction_id="x",
        patient_ref="patient-a",
        requested_by="dr-x",
        source=SOURCE,
        items=items,
        missing_information=(),
        provenance=PROVENANCE,
    )


def test_draft_is_always_pending_clinician_review():
    assert draft(COUGH).review_status is ReviewStatus.PENDING_CLINICIAN_REVIEW


def test_empty_draft_is_valid():
    assert draft().items == ()


@pytest.mark.parametrize("text", ["", "   ", "x" * (MAX_SOURCE_LENGTH + 1)])
def test_rejects_empty_or_oversized_source(text):
    with pytest.raises(InvalidExtraction):
        ExtractionSource(type=SourceType.TRANSCRIPT, text=text)


def test_rejects_evidence_that_does_not_match_source():
    wrong = replace(COUGH, evidence=Evidence(quote="Severe cough", start=0, end=12))
    with pytest.raises(InvalidExtraction):
        draft(wrong)


def test_rejects_confidence_outside_unit_interval():
    with pytest.raises(InvalidExtraction):
        draft(replace(COUGH, confidence=1.5))
