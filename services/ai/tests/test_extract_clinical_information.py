from datetime import UTC, datetime

from application.extract_clinical_information import (
    ExtractClinicalInformation,
    ExtractionRequest,
    ExtractorOutput,
)
from domain.clinical_extraction import (
    ExtractionSource,
    ExtractorInfo,
    ExtractorKind,
    MissingInformation,
    SourceType,
)

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


class FakeExtractor:
    info = ExtractorInfo(ExtractorKind.MODEL, "fake", "0", mocked=False)

    def __init__(self):
        self.seen = []

    def extract(self, source):
        self.seen.append(source)
        return ExtractorOutput(
            items=(), missing_information=(MissingInformation("allergies", "Ask."),)
        )


def test_builds_draft_with_provenance_from_extractor():
    extractor = FakeExtractor()
    use_case = ExtractClinicalInformation(
        extractor, clock=lambda: NOW, new_id=lambda: "id-1"
    )
    source = ExtractionSource(type=SourceType.LAB_REPORT, text="Hb 12.1 g/dL")

    result = use_case(
        ExtractionRequest(patient_ref="patient-a", requested_by="dr-x", source=source)
    )

    assert extractor.seen == [source]
    assert result.extraction_id == "id-1"
    assert result.provenance.extractor is FakeExtractor.info
    assert result.provenance.generated_at == NOW
    assert result.provenance.source_type is SourceType.LAB_REPORT
    assert result.missing_information[0].topic == "allergies"
