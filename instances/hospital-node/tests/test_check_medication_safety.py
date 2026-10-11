import pytest

from application.check_medication_safety import (
    ENGINE_NAME,
    CheckMedicationSafety,
    CheckNotPerformed,
    ExplanationUnavailable,
    RuleSourceUnavailable,
    SafetyCheckRequest,
    WarningExplanation,
)
from domain.medication_safety import SafetySourceKind
from tests.conftest import DEMO_NOW
from tests.test_medication_safety_domain import RULES, med, statement


class RuleSourceDouble:
    def __init__(self, mocked=False, available=True):
        self.mocked = mocked
        self.available = available

    def rule_set(self):
        if not self.available:
            raise RuleSourceUnavailable("/secret/path/rules.json missing")
        return RULES


def request(proposed=med("Alpha"), *current):
    return SafetyCheckRequest(
        patient_ref="pat-1",
        requested_by="clin-1",
        proposed_medication=proposed,
        current_medications=current or (statement("s-b", med("Bêta")),),
    )


def run(source, req=None):
    return CheckMedicationSafety(source, clock=lambda: DEMO_NOW, new_id=lambda: "c-1")(
        req or request()
    )


def test_records_the_engine_rule_set_and_whether_the_rules_are_mocked():
    result = run(RuleSourceDouble(mocked=True))

    assert (result.check_id, result.evaluated_at, result.mocked) == (
        "c-1",
        DEMO_NOW,
        True,
    )
    assert (result.engine.kind, result.engine.name) == (
        SafetySourceKind.DETERMINISTIC_RULE_SET,
        ENGINE_NAME,
    )
    assert [w.rule.rule_id for w in result.outcome.warnings] == ["r-ab"]


def test_without_a_rule_source_no_check_is_performed_and_nothing_leaks():
    with pytest.raises(CheckNotPerformed) as raised:
        run(RuleSourceDouble(available=False))

    assert "No check was performed" in str(raised.value)
    assert "/secret" not in str(raised.value)


def test_an_unknown_proposed_medication_is_not_checked():
    with pytest.raises(CheckNotPerformed, match="not_in_rule_source"):
        run(RuleSourceDouble(), request(med("Inconnu")))


class ExplainerDouble:
    def __init__(self, fail_on=()):
        self.fail_on = fail_on
        self.calls = []

    def explain(self, warning_id, warning, rules, requested_by):
        self.calls.append((warning_id, warning.rule.rule_id, requested_by))
        if warning.rule.rule_id in self.fail_on:
            raise ExplanationUnavailable("down")
        return WarningExplanation(
            text=f"Explication de {warning.rule.rule_id}.",
            generator_kind="deterministic_template",
            generator_name="t",
            generator_version="1",
            generator_mocked=False,
            generated_at="2026-10-11T10:00:00+00:00",
        )


def explained(explainer):
    req = request(
        med("Alpha"),
        statement("s-b", med("Bêta")),
        statement("s-c", med("Gamma")),
    )
    return CheckMedicationSafety(
        RuleSourceDouble(), clock=lambda: DEMO_NOW, explainer=explainer
    )(req)


def test_each_warning_gets_its_explanation_in_order():
    double = ExplainerDouble()
    result = explained(double)

    assert [w.rule.rule_id for w in result.outcome.warnings] == ["r-ac", "r-ab"]
    assert [e.text for e in result.explanations] == [
        "Explication de r-ac.",
        "Explication de r-ab.",
    ]
    assert sorted(double.calls) == [
        ("warning-1", "r-ac", "clin-1"),
        ("warning-2", "r-ab", "clin-1"),
    ]


def test_a_failed_explanation_is_null_and_the_warnings_are_unchanged():
    without = explained(None)
    failing = explained(ExplainerDouble(fail_on={"r-ab"}))

    assert failing.outcome == without.outcome
    assert [e is None for e in failing.explanations] == [False, True]
    assert without.explanations == (None, None)


def test_no_warning_means_no_explanation_is_asked():
    double = ExplainerDouble()
    result = CheckMedicationSafety(
        RuleSourceDouble(), clock=lambda: DEMO_NOW, explainer=double
    )(request(med("Bêta"), statement("s-c", med("Gamma"))))

    assert (result.explanations, double.calls) == ((), [])
