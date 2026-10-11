import pytest

from domain.medication_safety import (
    Coding,
    InteractionRule,
    InvalidRuleSet,
    Medication,
    MedicationStatement,
    ProposedMedicationNotEvaluable,
    RuleSet,
    SafetySourceKind,
    Severity,
    StatementSource,
    StatementStatus,
    UnevaluatedReason,
    check_interactions,
)

SYSTEM = "urn:test:medication"


def rule(rule_id, first, second, severity):
    return InteractionRule(rule_id, frozenset({first, second}), severity, "Effet.")


RULES = RuleSet(
    kind=SafetySourceKind.DETERMINISTIC_RULE_SET,
    name="test-rules",
    version="1",
    code_system=SYSTEM,
    medications={"A": "Alpha", "B": "Bêta", "C": "Gamma", "D": "Delta"},
    rules=(
        rule("r-ab", "A", "B", Severity.MINOR),
        rule("r-ac", "A", "C", Severity.CONTRAINDICATED),
        rule("r-ad", "A", "D", Severity.MAJOR),
    ),
)


def med(name, code=None, system=SYSTEM):
    return Medication(name, Coding(system, code) if code else None)


def statement(ref, medication, status=StatementStatus.ACTIVE, org="org-x"):
    return MedicationStatement(ref, medication, status, StatementSource(org))


def check(proposed, *current):
    return check_interactions(RULES, proposed, tuple(current))


def test_finds_each_interaction_and_points_back_to_its_statement():
    outcome = check(med("Alpha"), statement("s-b", med("Bêta", "B")))

    [warning] = outcome.warnings
    assert (warning.rule.rule_id, warning.conflicting.statement_ref) == ("r-ab", "s-b")
    assert outcome.warnings_found and outcome.unevaluated == ()


def test_warnings_are_ordered_most_severe_first():
    outcome = check(
        med("Alpha"),
        statement("s-b", med("Bêta")),
        statement("s-d", med("Delta")),
        statement("s-c", med("Gamma")),
    )

    assert [w.rule.severity for w in outcome.warnings] == [
        Severity.CONTRAINDICATED,
        Severity.MAJOR,
        Severity.MINOR,
    ]


def test_a_known_pair_without_a_rule_gives_no_warning():
    outcome = check(med("Bêta"), statement("s-c", med("Gamma")))

    assert (outcome.warnings, outcome.unevaluated) == ((), ())
    assert not outcome.warnings_found


def test_names_match_without_case_or_accents_and_codes_win_over_other_systems():
    outcome = check(
        med("ALPHA"),
        statement("s-b", med("beta")),
        # A code in another system is not ours: the name identifies it.
        statement("s-d", med("Delta", "999", system="urn:other")),
    )

    assert {w.rule.rule_id for w in outcome.warnings} == {"r-ab", "r-ad"}


@pytest.mark.parametrize(
    "medication, reason",
    [
        (med("Inconnu"), UnevaluatedReason.NOT_IN_RULE_SOURCE),
        (med("Bêta", "Z"), UnevaluatedReason.NOT_IN_RULE_SOURCE),
        (med("Bêta", "C"), UnevaluatedReason.AMBIGUOUS_MEDICATION),
    ],
    ids=["unknown-name", "unknown-code", "code-and-name-disagree"],
)
def test_a_medication_the_rules_cannot_identify_is_reported_not_guessed(
    medication, reason
):
    outcome = check(med("Alpha"), statement("s-1", medication))

    assert outcome.warnings == ()
    assert [(u.statement.statement_ref, u.reason) for u in outcome.unevaluated] == [
        ("s-1", reason)
    ]


def test_a_stopped_medication_is_skipped_and_an_unknown_status_is_reported():
    outcome = check(
        med("Alpha"),
        statement("s-stopped", med("Gamma"), StatementStatus.STOPPED),
        statement("s-unknown", med("Delta"), StatementStatus.UNKNOWN),
    )

    assert outcome.warnings == ()
    assert [(u.statement.statement_ref, u.reason) for u in outcome.unevaluated] == [
        ("s-unknown", UnevaluatedReason.STATUS_UNKNOWN)
    ]


def test_an_empty_history_gives_no_warning():
    assert check(med("Alpha")).warnings == ()


@pytest.mark.parametrize(
    "proposed",
    [med("Inconnu"), med("Alpha", "B")],
    ids=["unknown", "ambiguous"],
)
def test_an_unidentified_proposed_medication_cannot_be_checked(proposed):
    with pytest.raises(ProposedMedicationNotEvaluable):
        check(proposed, statement("s-b", med("Bêta")))


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"rules": (rule("r", "A", "Z", Severity.MAJOR),)}, "does not evaluate"),
        ({"rules": (RULES.rules[0], rule("r2", "B", "A", Severity.MAJOR))}, "repeats"),
        (
            {"rules": (InteractionRule("r", frozenset({"A"}), Severity.MAJOR, "x"),)},
            "two medications",
        ),
        ({"medications": {"A": "Alpha", "B": "alpha"}, "rules": ()}, "share a name"),
        ({"version": " "}, "version"),
    ],
)
def test_an_inconsistent_rule_set_is_refused(changes, message):
    fields = {**RULES.__dict__, **changes}
    with pytest.raises(InvalidRuleSet, match=message):
        RuleSet(**fields)
