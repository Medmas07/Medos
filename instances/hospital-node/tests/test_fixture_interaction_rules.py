import json
from pathlib import Path

import pytest

from adapters.outbound.fixture_interaction_rules import (
    FixtureInteractionRuleSource,
    RuleFixtureError,
)
from domain.medication_safety import SafetySourceKind

DEMO_RULES = Path(__file__).resolve().parents[3] / "demo-data" / "medication-rules.json"


def test_loads_the_fictional_demo_rule_set_as_mocked():
    source = FixtureInteractionRuleSource.load(DEMO_RULES)
    rules = source.rule_set()

    assert source.mocked is True
    assert (rules.kind, rules.name, rules.version) == (
        SafetySourceKind.DETERMINISTIC_RULE_SET,
        "demo-interaction-rules",
        "1.0.0",
    )
    # Bronchair is in the catalog but not evaluated by the rule set.
    assert "MED-BRONCHAIR" not in rules.medications
    assert len(rules.rules) == 4


def broken(tmp_path, mutate):
    fixture = json.loads(DEMO_RULES.read_text(encoding="utf-8"))
    mutate(fixture)
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda f: f.update(fictional=False), "not marked fictional"),
        (lambda f: f["ruleSet"].update(validated=True), "validated: false"),
        (lambda f: f["ruleSet"].update(kind="llm"), "Invalid"),
        (lambda f: f["ruleSet"].pop("codeSystem"), "Invalid"),
        (
            lambda f: f["interactionRules"][0].update(severity="critical"),
            "Invalid",
        ),
        (
            lambda f: f["interactionRules"][0].update(
                medicationCodes=["MED-COAGULIX", "MED-BRONCHAIR"]
            ),
            "does not evaluate",
        ),
    ],
)
def test_refuses_anything_but_a_fictional_deterministic_rule_set(
    tmp_path, mutate, message
):
    with pytest.raises(RuleFixtureError, match=message):
        FixtureInteractionRuleSource.load(broken(tmp_path, mutate))


def test_a_missing_file_stops_startup(tmp_path):
    with pytest.raises(RuleFixtureError, match="Cannot read"):
        FixtureInteractionRuleSource.load(tmp_path / "missing.json")
