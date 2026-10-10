from adapters.outbound.fixture_document_reviewer import FixtureDocumentReviewer
from domain.document_review import Dossier, DossierField, FindingCategory, ReviewerKind


def test_fixed_rules_label_themselves_as_mocked_not_ai():
    output = FixtureDocumentReviewer().review(
        Dossier(
            fields=(
                DossierField("administrative_profile.security_contact", None),
                DossierField(
                    "technical_questionnaire.test_environment_available", True
                ),
                DossierField("technical_questionnaire.outbound_https_allowed", False),
            )
        )
    )

    assert [(f.category, f.field_paths) for f in output.findings] == [
        (
            FindingCategory.MISSING_INFORMATION,
            ("administrative_profile.security_contact",),
        ),
        (
            FindingCategory.CLARIFICATION_NEEDED,
            ("technical_questionnaire.outbound_https_allowed",),
        ),
    ]
    assert (output.reviewer.kind, output.reviewer.mocked) == (
        ReviewerKind.DETERMINISTIC_FIXTURE,
        True,
    )
    assert "no language model was called" in output.uncertainty_notes[0]


def test_nothing_to_report_is_an_empty_review():
    output = FixtureDocumentReviewer().review(
        Dossier(
            fields=(DossierField("administrative_profile.security_contact", "Sami"),)
        )
    )

    assert output.findings == ()
