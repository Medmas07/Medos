import pytest

from application.check_medication_safety import (
    ENGINE_NAME,
    CheckMedicationSafety,
    CheckNotPerformed,
    RuleSourceUnavailable,
    SafetyCheckRequest,
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
