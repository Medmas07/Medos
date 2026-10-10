"""MOCKED extractor for the D1 demo (HC-152). It is not clinical intelligence.

It recognises only the fictional canonical consultation transcript below and
returns a fixed draft for it. Any other text yields an empty draft. Patient A,
Dr. X, Hospital B, and Medication A are fictional demo entities.
"""

from application.extract_clinical_information import ExtractorOutput
from domain.clinical_extraction import (
    Evidence,
    ExtractedItem,
    ExtractionSource,
    ExtractorInfo,
    ExtractorKind,
    ItemCategory,
    MissingInformation,
    SourceType,
)

DEMO_TRANSCRIPT = (
    "Patient A reports a headache for three days, rated 6 out of 10, with mild "
    "nausea. Temperature is 38.2 °C. Blood pressure is 150/95 mmHg. Patient A "
    "is currently taking Medication A, prescribed at Hospital B. Plan to "
    "review in one week."
)


FIXTURE_INFO = ExtractorInfo(
    kind=ExtractorKind.DETERMINISTIC_FIXTURE,
    name="demo-fixture-extractor",
    version="1.0.0",
    mocked=True,
)


def _evidence(quote: str) -> Evidence:
    start = DEMO_TRANSCRIPT.index(quote)
    return Evidence(quote=quote, start=start, end=start + len(quote))


DEMO_OUTPUT = ExtractorOutput(
    items=(
        ExtractedItem(
            item_id="item-1",
            category=ItemCategory.SYMPTOM,
            text="Headache for three days, severity 6/10",
            evidence=_evidence("a headache for three days, rated 6 out of 10"),
        ),
        ExtractedItem(
            item_id="item-2",
            category=ItemCategory.SYMPTOM,
            text="Mild nausea",
            evidence=_evidence("mild nausea"),
        ),
        ExtractedItem(
            item_id="item-3",
            category=ItemCategory.MEASUREMENT,
            text="Body temperature 38.2 °C",
            evidence=_evidence("Temperature is 38.2 °C"),
            value=38.2,
            unit="°C",
            abnormal=True,
        ),
        ExtractedItem(
            item_id="item-4",
            category=ItemCategory.MEASUREMENT,
            text="Systolic blood pressure 150 mmHg",
            evidence=_evidence("Blood pressure is 150/95 mmHg"),
            value=150,
            unit="mmHg",
            abnormal=True,
        ),
        ExtractedItem(
            item_id="item-5",
            category=ItemCategory.MEASUREMENT,
            text="Diastolic blood pressure 95 mmHg",
            evidence=_evidence("Blood pressure is 150/95 mmHg"),
            value=95,
            unit="mmHg",
            abnormal=True,
        ),
        ExtractedItem(
            item_id="item-6",
            category=ItemCategory.MEDICATION,
            text="Medication A (current, prescribed at Hospital B)",
            evidence=_evidence(
                "currently taking Medication A, prescribed at Hospital B"
            ),
        ),
        ExtractedItem(
            item_id="item-7",
            category=ItemCategory.FOLLOW_UP_ACTION,
            text="Review in one week",
            evidence=_evidence("review in one week"),
        ),
    ),
    missing_information=(
        MissingInformation(
            topic="allergies",
            prompt="Known allergies are not mentioned.",
        ),
        MissingInformation(
            topic="medication_dose",
            prompt="Dose and frequency of Medication A are not mentioned.",
        ),
    ),
    info=FIXTURE_INFO,
)

EMPTY_OUTPUT = ExtractorOutput(items=(), missing_information=(), info=FIXTURE_INFO)


class FixtureClinicalExtractor:
    info = FIXTURE_INFO

    def extract(self, source: ExtractionSource) -> ExtractorOutput:
        if source.type is SourceType.TRANSCRIPT and source.text == DEMO_TRANSCRIPT:
            return DEMO_OUTPUT
        return EMPTY_OUTPUT
