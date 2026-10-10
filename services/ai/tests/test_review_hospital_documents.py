from datetime import UTC, datetime

from application.review_hospital_documents import (
    ReviewerOutput,
    ReviewHospitalDocuments,
    ReviewRequest,
)
from domain.document_review import (
    DocumentQuote,
    FindingCategory,
    ReviewerInfo,
    ReviewerKind,
    ReviewFinding,
    ReviewStatus,
)
from tests.test_document_review_domain import DOSSIER

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
INFO = ReviewerInfo(ReviewerKind.MODEL, "claude-agent-sdk", "claude-opus-5-5", False)


class ScriptedReviewer:
    """Test double at the DocumentReviewer port."""

    def __init__(self, findings, uncited=0):
        self.output = ReviewerOutput(tuple(findings), INFO, ("note",), uncited)

    def review(self, dossier):
        return self.output


def proposal(paths, evidence=None, category=FindingCategory.INCONSISTENCY):
    return ReviewFinding("proposal-x", category, "Message.", tuple(paths), evidence)


def test_keeps_cited_findings_renumbers_them_and_counts_the_others():
    reviewer = ScriptedReviewer(
        [
            proposal(["technical_questionnaire.invented"]),
            proposal(
                ["technical_questionnaire.database"],
                DocumentQuote("doc-c-architecture", "PostgreSQL 12"),
            ),
            proposal(
                ["administrative_profile.security_contact"],
                category=FindingCategory.MISSING_INFORMATION,
            ),
        ],
        uncited=2,
    )
    review = ReviewHospitalDocuments(reviewer, clock=lambda: NOW, new_id=lambda: "r-1")(
        ReviewRequest("app-hospital-c", "usr-mehdi", DOSSIER)
    )

    assert [(f.finding_id, f.field_paths) for f in review.findings] == [
        ("finding-1", ("technical_questionnaire.database",)),
        ("finding-2", ("administrative_profile.security_contact",)),
    ]
    assert review.unverified_findings_dropped == 3  # 1 unverifiable + 2 uncited
    assert (review.advisory, review.review_status) == (
        True,
        ReviewStatus.PENDING_HUMAN_REVIEW,
    )
    assert (review.reviewer, review.uncertainty_notes, review.generated_at) == (
        INFO,
        ("note",),
        NOW,
    )


def test_no_finding_is_a_valid_review():
    review = ReviewHospitalDocuments(ScriptedReviewer([]), clock=lambda: NOW)(
        ReviewRequest("app-hospital-c", "usr-mehdi", DOSSIER)
    )

    assert (review.findings, review.unverified_findings_dropped) == ((), 0)
