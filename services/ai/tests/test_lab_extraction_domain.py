import pytest

from domain.lab_extraction import (
    FlagBasis,
    InvalidLabExtraction,
    LabFlag,
    ProposedResult,
    ReferenceRange,
    flag_for,
    numbers_in,
    verified,
)

REPORT = """Bilan de contrôle (fictif)
Potassium : 5,6 mmol/L (3,5 – 5,0)
Sodium : 131 mmol/L (135 – 145)
CRP : 3 mg/L"""


@pytest.mark.parametrize(
    "value, flag",
    [
        (3.4, LabFlag.LOW),
        (3.5, LabFlag.NORMAL),
        (5.0, LabFlag.NORMAL),
        (5.6, LabFlag.HIGH),
    ],
)
def test_the_flag_is_computed_from_the_printed_range(value, flag):
    assert flag_for(value, ReferenceRange(3.5, 5.0)) is flag


def test_no_range_means_no_flag():
    assert flag_for(5.6, None) is None


def test_reads_decimal_commas_and_points():
    assert numbers_in("Potassium : 5,6 mmol/L (3,5 – 5.0)") == [5.6, 3.5, 5.0]


def test_a_verified_result_is_flagged_here_not_by_the_extractor():
    result = verified(
        ProposedResult(
            "Potassium",
            5.6,
            "mmol/L",
            "Potassium : 5,6 mmol/L (3,5 – 5,0)",
            ReferenceRange(3.5, 5.0),
        ),
        REPORT,
        "result-1",
    )

    assert (result.flag, result.flag_basis) == (LabFlag.HIGH, FlagBasis.REFERENCE_RANGE)
    assert REPORT[result.evidence.start : result.evidence.end] == result.evidence.quote


def test_a_low_value_is_flagged_low():
    result = verified(
        ProposedResult(
            "Sodium",
            131,
            "mmol/L",
            "Sodium : 131 mmol/L (135 – 145)",
            ReferenceRange(135, 145),
        ),
        REPORT,
        "result-1",
    )

    assert result.flag is LabFlag.LOW


def test_a_range_not_printed_in_the_quote_is_not_used():
    # The model supplies a "usual" range the report does not print.
    result = verified(
        ProposedResult("CRP", 3, "mg/L", "CRP : 3 mg/L", ReferenceRange(0, 5)),
        REPORT,
        "result-1",
    )

    assert (result.reference_range, result.flag, result.flag_basis) == (
        None,
        None,
        FlagBasis.NO_REFERENCE_RANGE,
    )


@pytest.mark.parametrize(
    "proposal",
    [
        # A value the quote does not print.
        ProposedResult(
            "Potassium", 4.6, "mmol/L", "Potassium : 5,6 mmol/L (3,5 – 5,0)"
        ),
        # A quote not in the report.
        ProposedResult(
            "Potassium", 5.6, "mmol/L", "Potassium : 5,6 mmol/L (3,5 – 5,5)"
        ),
        ProposedResult(" ", 5.6, "mmol/L", "Potassium : 5,6 mmol/L"),
        ProposedResult("Potassium", 5.6, "", "Potassium : 5,6 mmol/L"),
        ProposedResult("Potassium", 5.6, "mmol/L", "  "),
    ],
)
def test_an_unsupported_result_is_dropped(proposal):
    assert verified(proposal, REPORT, "result-1") is None


def test_a_case_only_difference_keeps_the_reports_characters():
    result = verified(
        ProposedResult(
            "Potassium", 5.6, "mmol/L", "POTASSIUM : 5,6 MMOL/L (3,5 – 5,0)"
        ),
        REPORT,
        "result-1",
    )

    assert result.evidence.quote == "Potassium : 5,6 mmol/L (3,5 – 5,0)"


def test_a_range_with_low_above_high_is_invalid():
    with pytest.raises(InvalidLabExtraction):
        ReferenceRange(5.0, 3.5)
