from dataclasses import replace

import pytest

from domain.priority_explanation import (
    MAX_EXPLANATION_LENGTH,
    FactorType,
    InvalidQueueEntry,
    Level,
    MethodKind,
    PriorityFactor,
    PriorityMethod,
    QueueEntry,
    displayed_text,
    guardrail_problems,
    template_text,
)

# demo-data/clinician.json, queue-clin-x-1, without its patient reference.
ENTRY = QueueEntry(
    entry_id="queue-clin-x-1",
    rank=1,
    priority=Level.HIGH,
    score=82,
    factors=(
        PriorityFactor(
            "alert-b-hba1c",
            FactorType.ABNORMAL_LAB,
            "Résultat biologique anormal non revu",
            Level.HIGH,
        ),
        PriorityFactor(
            "alert-b-followup",
            FactorType.MISSED_FOLLOW_UP,
            "Suivi en retard",
            Level.MEDIUM,
        ),
    ),
    method=PriorityMethod(
        MethodKind.DETERMINISTIC_MOCK,
        "Priorité fictive de démonstration",
        "1.0",
        "Score = somme de poids fixes par type d'alerte non résolue. Méthode de "
        "démonstration, non validée cliniquement, qui ne remplace pas le jugement "
        "clinique.",
    ),
)
GOOD = (
    "Ce patient est en priorité haute, au rang 1 de la file avec un score de 82, pour "
    "deux raisons : un résultat biologique anormal qui n'a pas encore été revu, de "
    "sévérité haute [F1], et un suivi en retard, de sévérité moyenne "
    "[F2]. Ce classement vient d'une méthode de démonstration simulée ; "
    "ce n'est pas un triage clinique. La décision appartient au clinicien."
)


def test_a_faithful_explanation_passes():
    assert guardrail_problems(GOOD, ENTRY) == []


def test_citations_are_removed_from_the_displayed_text():
    assert displayed_text("Suivi en retard [F2].") == "Suivi en retard."


def test_english_and_accentless_text_passes():
    text = (
        "HIGH PRIORITY, rank 1, score 82: an abnormal lab result not yet reviewed "
        "[F1] and a late follow-up [F2]. This ranking is not "
        "a clinical triage; the decision belongs to the clinician."
    )

    assert guardrail_problems(text, ENTRY) == []


def test_a_factor_severity_is_not_a_priority():
    # "sévérité moyenne" describes a factor; only "priorité moyenne" names a priority.
    assert "names a priority" not in " ".join(guardrail_problems(GOOD, ENTRY))


def test_words_and_numbers_of_the_entry_itself_are_allowed():
    entry = replace(
        ENTRY,
        factors=(
            PriorityFactor(
                "alert-1",
                FactorType.PATIENT_DETERIORATION,
                "Détérioration signalée, saturation 89 %",
                Level.HIGH,
                weight=40,
            ),
        ),
    )
    text = (
        "Priorité haute [F1] : détérioration signalée, saturation 89 %, poids 40. "
        "La décision appartient au clinicien."
    )

    assert guardrail_problems(text, entry) == []


@pytest.mark.parametrize(
    "text, problem",
    [
        ("", "the explanation is empty"),
        ("[F1] [F2]", "the explanation is empty"),
        (
            GOOD.replace(" [F2]", ""),
            "does not cite the factor alert-b-followup",
        ),
        (GOOD + " [F3]", "cites [F3], which is not in the entry"),
        (GOOD + " [alert-b-hba1c]", "cites [alert-b-hba1c], which is not in the entry"),
        (GOOD.replace("priorité haute", "priorité élevée"), None),
        (
            GOOD.replace("priorité haute", "position notable"),
            "does not state the priority high",
        ),
        (GOOD + " Priorité moyenne pour le suivi.", "names a priority other than high"),
        (GOOD.replace("82", "91"), "a number that is not in the entry: 91"),
        (GOOD + " L'HbA1c est à 8,9 %.", "a number that is not in the entry: 8.9"),
        (GOOD + " Cas urgent.", "claims an urgency"),
        (GOOD + " Il n'y a pas d'urgence vitale.", "claims an urgency"),
        (
            GOOD + " Cela suggère un diabète mal contrôlé.",
            "interprets the patient's condition",
        ),
        (
            GOOD + " Diagnostic probable : diabète.",
            "interprets the patient's condition",
        ),
        (GOOD + " Il est recommandé de le revoir.", "tells the clinician what to do"),
        (GOOD + " Voir ce patient en premier.", "tells the clinician what to do"),
        (GOOD + " You should call the patient.", "tells the clinician what to do"),
        (GOOD + " x" * MAX_EXPLANATION_LENGTH, "longer than 800 characters"),
    ],
)
def test_unfaithful_explanations_are_caught(text, problem):
    problems = guardrail_problems(text, ENTRY)

    if problem is None:
        assert problems == []
    else:
        assert any(problem in p for p in problems), problems


def test_the_template_restates_the_entry():
    assert template_text(ENTRY) == (
        "Priorité haute, rang 1 dans la file, score 82, selon la méthode « Priorité "
        "fictive de démonstration » (version 1.0, simulée), à partir de : Résultat "
        "biologique anormal non revu (sévérité haute) ; Suivi en retard (sévérité "
        "moyenne). Ce classement n'est pas un triage clinique. La décision appartient "
        "au clinicien."
    )


def test_the_template_of_a_real_rule_set_without_score_says_neither():
    entry = replace(
        ENTRY,
        rank=3,
        priority=Level.LOW,
        score=None,
        method=PriorityMethod(MethodKind.DETERMINISTIC_RULE_SET, "Règles", "2"),
    )

    text = template_text(entry)

    assert text.startswith("Priorité basse, rang 3 dans la file, selon la méthode")
    assert "score" not in text and "simulée" not in text


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"rank": 0}, "rank"),
        ({"factors": ()}, "1-10 factors"),
        ({"factors": (ENTRY.factors[0],) * 2}, "unique"),
        (
            {"factors": (replace(ENTRY.factors[0], factor_id="Dr X"),)},
            "opaque reference",
        ),
        ({"factors": (replace(ENTRY.factors[0], label=" "),)}, "factor label"),
        ({"method": replace(ENTRY.method, name="")}, "method.name"),
    ],
)
def test_an_invalid_entry_is_refused(changes, message):
    with pytest.raises(InvalidQueueEntry, match=message):
        replace(ENTRY, **changes)
