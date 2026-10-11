import pytest

from domain.medication_explanation import (
    MAX_EXPLANATION_LENGTH,
    InvalidWarning,
    MedicationWarning,
    RuleSource,
    SafetySourceKind,
    Severity,
    guardrail_problems,
    template_text,
)

WARNING = MedicationWarning(
    warning_id="warning-1",
    severity=Severity.MAJOR,
    summary="Risque hémorragique accru.",
    proposed_medication="Dolorane",
    conflicting_medication="Coagulix",
    rule_source=RuleSource(
        SafetySourceKind.DETERMINISTIC_RULE_SET,
        "Règles fictives de démonstration",
        "1.0",
        "rule-coagulix-dolorane",
    ),
)
GOOD = (
    "Dolorane et Coagulix interagissent : l'association expose à un risque "
    "hémorragique accru. Interaction majeure selon la source de règles. La décision "
    "appartient au clinicien."
)


def test_a_faithful_explanation_passes():
    assert guardrail_problems(GOOD, WARNING) == []


def test_saying_the_decision_to_prescribe_is_the_clinicians_is_not_a_directive():
    text = GOOD.replace("La décision", "La décision de prescrire")

    assert guardrail_problems(text, WARNING) == []


def test_matching_ignores_case_and_accents_and_whole_words_only():
    text = (
        "DOLORANE et coagulix : majoration du risque hémorragique, interaction majeure."
    )

    assert guardrail_problems(text, WARNING) == []


@pytest.mark.parametrize(
    "text, problem",
    [
        ("", "the explanation is empty"),
        ("Dolorane augmente le risque hémorragique.", "does not name Coagulix"),
        # Seen live: a small model called a major interaction merely "importante".
        (
            "La combinaison de Dolorane et Coagulix peut augmenter le risque de "
            "hémorragie. Cette interaction est considérée comme importante.",
            "does not state the severity major",
        ),
        (GOOD + " Elle reste toutefois mineure.", "names a severity other than major"),
        (GOOD + " Association contre-indiquée.", "names a severity other than major"),
        (GOOD + " Réduire Dolorane à 500 mg.", "contains a dose"),
        (GOOD + " Donner 1 comprimé.", "contains a dose"),
        (GOOD + " Limiter à 2 fois par jour.", "contains a dose"),
        # Seen live: a small model added a recommendation the warning does not make.
        (
            "Le conseil de traitement recommande de ne pas associer Dolorane et "
            "Coagulix : interaction majeure.",
            "tells the clinician what to do",
        ),
        (GOOD + " Il faut éviter Dolorane.", "tells the clinician what to do"),
        (GOOD + " Stop Coagulix first.", "tells the clinician what to do"),
        (GOOD + " x" * MAX_EXPLANATION_LENGTH, "longer than"),
    ],
)
def test_unsafe_or_unfaithful_text_is_refused(text, problem):
    problems = guardrail_problems(text, WARNING)

    assert any(problem in p for p in problems), problems


def test_the_template_restates_the_warning_and_passes_its_own_checks():
    text = template_text(WARNING)

    assert text == (
        "Interaction majeure entre Dolorane et Coagulix selon Règles fictives de "
        "démonstration (règle rule-coagulix-dolorane) : Risque hémorragique accru. "
        "La décision appartient au clinicien."
    )
    for severity in Severity:
        warning = MedicationWarning(**{**WARNING.__dict__, "severity": severity})
        assert guardrail_problems(template_text(warning), warning) == []


def test_a_warning_needs_its_content():
    with pytest.raises(InvalidWarning):
        MedicationWarning(**{**WARNING.__dict__, "summary": " "})
