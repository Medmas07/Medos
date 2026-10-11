"""Deterministic drug-drug interaction check (HC-162).

The engine compares a proposed medication with the patient's current medications, using
a rule set that a deterministic rule source or a validated source provides
(medication-safety-check.v1.yaml). It never uses a model. It never decides: every
warning awaits clinician review, and finding none is not a statement that a
prescription is safe.

A medication is identified in the rule set by its code in the rule set's code system,
otherwise by its exact name (case and accents ignored). A code and a name that point to
different medications are ambiguous, and nothing is guessed. Only active statements are
evaluated: a stopped medication is not current, and one whose status is unknown is
reported, not assumed.
"""

import unicodedata
from dataclasses import dataclass
from enum import Enum


class InvalidRuleSet(ValueError):
    pass


class ProposedMedicationNotEvaluable(Exception):
    """The rule set cannot identify the proposed medication: no check is possible."""

    def __init__(self, reason: "UnevaluatedReason") -> None:
        super().__init__(reason.value)
        self.reason = reason


class SafetySourceKind(Enum):
    # The only safety sources the contract allows. An LLM is not one of them.
    DETERMINISTIC_RULE_SET = "deterministic_rule_set"
    VALIDATED_SOURCE = "validated_source"


class Severity(Enum):
    # Most severe first: warnings are returned in this order.
    CONTRAINDICATED = "contraindicated"
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"


class StatementStatus(Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class UnevaluatedReason(Enum):
    NOT_IN_RULE_SOURCE = "not_in_rule_source"
    AMBIGUOUS_MEDICATION = "ambiguous_medication"
    STATUS_UNKNOWN = "status_unknown"


def _folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.strip().casefold())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


@dataclass(frozen=True)
class Coding:
    system: str
    code: str
    display: str | None = None


@dataclass(frozen=True)
class Medication:
    name: str
    code: Coding | None = None


@dataclass(frozen=True)
class StatementSource:
    organization_ref: str
    recorded_at: str | None = None


@dataclass(frozen=True)
class MedicationStatement:
    statement_ref: str
    medication: Medication
    status: StatementStatus
    source: StatementSource


@dataclass(frozen=True)
class InteractionRule:
    rule_id: str
    medication_codes: frozenset[str]
    severity: Severity
    summary: str
    reference: str | None = None


@dataclass(frozen=True)
class RuleSet:
    kind: SafetySourceKind
    name: str
    version: str
    code_system: str
    # Code -> name of every medication the rule set evaluates.
    medications: dict[str, str]
    rules: tuple[InteractionRule, ...]

    def __post_init__(self) -> None:
        for field in ("name", "version", "code_system"):
            if not getattr(self, field).strip():
                raise InvalidRuleSet(f"{field} is required")
        names = [_folded(n) for n in self.medications.values()]
        if len(set(names)) != len(names):
            raise InvalidRuleSet("two evaluated medications share a name")
        pairs: set[frozenset[str]] = set()
        for rule in self.rules:
            if len(rule.medication_codes) != 2:
                raise InvalidRuleSet(f"{rule.rule_id} must name two medications")
            if not rule.medication_codes <= self.medications.keys():
                raise InvalidRuleSet(
                    f"{rule.rule_id} names a medication the rule set does not evaluate"
                )
            if rule.medication_codes in pairs:
                raise InvalidRuleSet(f"{rule.rule_id} repeats a medication pair")
            pairs.add(rule.medication_codes)

    def rule_for(self, first: str, second: str) -> InteractionRule | None:
        pair = frozenset({first, second})
        return next((r for r in self.rules if r.medication_codes == pair), None)

    def identify(self, medication: Medication) -> str | UnevaluatedReason:
        """The medication's code in this rule set, or why it cannot be evaluated."""
        by_name = next(
            (
                code
                for code, name in self.medications.items()
                if _folded(name) == _folded(medication.name)
            ),
            None,
        )
        by_code = None
        if medication.code is not None and medication.code.system == self.code_system:
            by_code = medication.code.code
            if by_code not in self.medications:
                return UnevaluatedReason.NOT_IN_RULE_SOURCE
        if by_code and by_name and by_code != by_name:
            return UnevaluatedReason.AMBIGUOUS_MEDICATION
        found = by_code or by_name
        return found if found is not None else UnevaluatedReason.NOT_IN_RULE_SOURCE


@dataclass(frozen=True)
class InteractionWarning:
    rule: InteractionRule
    proposed_medication: Medication
    conflicting: MedicationStatement


@dataclass(frozen=True)
class Unevaluated:
    statement: MedicationStatement
    reason: UnevaluatedReason


@dataclass(frozen=True)
class CheckOutcome:
    warnings: tuple[InteractionWarning, ...]
    unevaluated: tuple[Unevaluated, ...]

    @property
    def warnings_found(self) -> bool:
        return bool(self.warnings)


_SEVERITY_ORDER = list(Severity)


def check_interactions(
    rules: RuleSet,
    proposed: Medication,
    current: tuple[MedicationStatement, ...],
) -> CheckOutcome:
    proposed_code = rules.identify(proposed)
    if isinstance(proposed_code, UnevaluatedReason):
        raise ProposedMedicationNotEvaluable(proposed_code)
    warnings: list[InteractionWarning] = []
    unevaluated: list[Unevaluated] = []
    for statement in current:
        if statement.status is StatementStatus.STOPPED:
            continue
        if statement.status is StatementStatus.UNKNOWN:
            unevaluated.append(Unevaluated(statement, UnevaluatedReason.STATUS_UNKNOWN))
            continue
        code = rules.identify(statement.medication)
        if isinstance(code, UnevaluatedReason):
            unevaluated.append(Unevaluated(statement, code))
            continue
        rule = rules.rule_for(proposed_code, code)
        if rule is not None:
            warnings.append(InteractionWarning(rule, proposed, statement))
    warnings.sort(key=lambda w: _SEVERITY_ORDER.index(w.rule.severity))
    return CheckOutcome(tuple(warnings), tuple(unevaluated))
