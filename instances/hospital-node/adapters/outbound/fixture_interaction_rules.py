"""MOCKED interaction rule source for the demo (HC-162).

Reads the fictional deterministic rule set of demo-data/medication-rules.json (HC-161)
at startup. It is not a validated pharmacological source (HC-163): the file must be
marked fictional and its rules `validated: false`, and every result built on it is
reported as mocked. A file that cannot be read or is not a deterministic rule set stops
startup; the node never falls back to checking without rules.
"""

import json
from pathlib import Path

from domain.medication_safety import (
    InteractionRule,
    InvalidRuleSet,
    RuleSet,
    SafetySourceKind,
    Severity,
)


class RuleFixtureError(RuntimeError):
    pass


class FixtureInteractionRuleSource:
    mocked = True

    def __init__(self, rules: RuleSet) -> None:
        self._rules = rules

    @classmethod
    def load(cls, path: Path) -> "FixtureInteractionRuleSource":
        try:
            fixture = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise RuleFixtureError(
                f"Cannot read medication rule fixture {path}: {error}"
            ) from error
        if fixture.get("fictional") is not True:
            raise RuleFixtureError(f"{path} is not marked fictional.")
        try:
            meta = fixture["ruleSet"]
            if meta.get("validated") is not False:
                raise RuleFixtureError(f"{path}: demo rules must be validated: false.")
            names = {m["code"]: m["name"] for m in fixture["medications"]}
            rules = RuleSet(
                kind=SafetySourceKind(meta["kind"]),
                name=meta["name"],
                version=meta["version"],
                code_system=meta["codeSystem"],
                medications={c: names[c] for c in meta["evaluatedMedicationCodes"]},
                rules=tuple(
                    InteractionRule(
                        rule_id=r["id"],
                        medication_codes=frozenset(r["medicationCodes"]),
                        severity=Severity(r["severity"]),
                        summary=r["effect"],
                    )
                    for r in fixture["interactionRules"]
                ),
            )
        except (KeyError, TypeError, ValueError, InvalidRuleSet) as error:
            raise RuleFixtureError(
                f"Invalid medication rule fixture {path}: {error}"
            ) from error
        return cls(rules)

    def rule_set(self) -> RuleSet:
        return self._rules
