"""Validated interaction rule source read from a versioned snapshot (HC-163).

The snapshot is a transcription of a published, validated interaction list, kept in
reference/ with its citation, version, and every correction or exclusion. The only one
today is the ONC high-priority list (Phansalkar et al., JAMIA 2012): a minimum set of
contraindicated pairs, by drug class with the members the source lists. Each class
pair becomes one rule per member pair, all citing the same source row. Read once at
startup, no network; results are not mocked. A file that is not a consistent
validated_source snapshot stops startup.
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

ONC_HIGH_PRIORITY_2012 = (
    Path(__file__).resolve().parents[2]
    / "reference"
    / "onc-high-priority-ddi-2012.json"
)


class SnapshotError(RuntimeError):
    pass


class ValidatedSnapshotRuleSource:
    mocked = False

    def __init__(self, rules: RuleSet) -> None:
        self._rules = rules

    @classmethod
    def load(cls, path: Path) -> "ValidatedSnapshotRuleSource":
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise SnapshotError(
                f"Cannot read interaction snapshot {path}: {error}"
            ) from error
        try:
            meta = snapshot["ruleSet"]
            kind = SafetySourceKind(meta["kind"])
            if kind is not SafetySourceKind.VALIDATED_SOURCE:
                raise SnapshotError(f"{path} is not a validated_source snapshot.")
            reference = f"{meta['citation']} {meta['url']}"
            rules = tuple(
                InteractionRule(
                    rule_id=interaction["id"],
                    medication_codes=frozenset({first, second}),
                    severity=Severity(interaction["severity"]),
                    summary=interaction["summary"],
                    reference=reference,
                )
                for interaction in snapshot["interactions"]
                for first in interaction["object"]
                for second in interaction["precipitant"]
            )
            ingredients = snapshot["ingredients"]
            rule_set = RuleSet(
                kind=kind,
                name=meta["name"],
                version=meta["version"],
                code_system=meta["codeSystem"],
                medications={i["code"]: i["name"] for i in ingredients},
                rules=rules,
                synonyms={s: i["code"] for i in ingredients for s in i["synonyms"]},
                scope_note=meta["scopeNote"],
            )
        except (KeyError, TypeError, ValueError, InvalidRuleSet) as error:
            raise SnapshotError(
                f"Invalid interaction snapshot {path}: {error}"
            ) from error
        return cls(rule_set)

    def rule_set(self) -> RuleSet:
        return self._rules
