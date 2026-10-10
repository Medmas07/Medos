from adapters.outbound.fixture_extractor import (
    DEMO_TRANSCRIPT,
    FixtureClinicalExtractor,
)
from domain.clinical_extraction import ExtractionSource, ItemCategory, SourceType

extractor = FixtureClinicalExtractor()


def test_is_labelled_as_mocked():
    assert extractor.info.mocked is True


def test_demo_transcript_yields_reviewable_items():
    output = extractor.extract(ExtractionSource(SourceType.TRANSCRIPT, DEMO_TRANSCRIPT))

    categories = {item.category for item in output.items}
    assert {
        ItemCategory.SYMPTOM,
        ItemCategory.MEASUREMENT,
        ItemCategory.MEDICATION,
    } <= categories
    for item in output.items:
        assert (
            DEMO_TRANSCRIPT[item.evidence.start : item.evidence.end]
            == item.evidence.quote
        )
    assert output.missing_information


def test_unknown_text_yields_empty_output():
    output = extractor.extract(
        ExtractionSource(SourceType.TRANSCRIPT, "Unrelated note.")
    )
    assert output.items == () and output.missing_information == ()
