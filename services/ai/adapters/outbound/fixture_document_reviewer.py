"""MOCKED hospital dossier reviewer (HC-154, AI_REVIEW_MODE=fixture).

Fixed rules stand in for a language model, like the Hospital Portal's simulated review
(HC-057): no model is called, the findings are deterministic, and they are labelled
`deterministic_fixture` and `mocked`. For offline demos only; it is not AI.
"""

from application.review_hospital_documents import ReviewerOutput
from domain.document_review import (
    Dossier,
    FindingCategory,
    ReviewerInfo,
    ReviewerKind,
    ReviewFinding,
)

INFO = ReviewerInfo(
    kind=ReviewerKind.DETERMINISTIC_FIXTURE,
    name="fixture-document-reviewer",
    version="hc-154-v1",
    mocked=True,
)

# (path, value that triggers it, category, message), checked in order.
RULES = (
    (
        "administrative_profile.security_contact",
        None,
        FindingCategory.MISSING_INFORMATION,
        "Aucun contact de sécurité distinct n'est indiqué.",
    ),
    (
        "technical_questionnaire.test_environment_available",
        False,
        FindingCategory.CLARIFICATION_NEEDED,
        "Pas d'environnement de test du DMI : l'adaptateur devra être vérifié sur des "
        "données fictives.",
    ),
    (
        "technical_questionnaire.outbound_https_allowed",
        False,
        FindingCategory.CLARIFICATION_NEEDED,
        "Les connexions HTTPS sortantes sont refusées : la connectivité du futur "
        "Hospital Node est à vérifier.",
    ),
)


class FixtureDocumentReviewer:
    def review(self, dossier: Dossier) -> ReviewerOutput:
        values = {f.path: f.value for f in dossier.fields}
        findings = tuple(
            ReviewFinding(f"fixture-{number}", category, message, (path,))
            for number, (path, trigger, category, message) in enumerate(RULES, start=1)
            if path in values and values[path] is trigger
        )
        return ReviewerOutput(
            findings=findings,
            reviewer=INFO,
            uncertainty_notes=(
                "Deterministic demo rules (MOCKED): no language model was called.",
            ),
        )
