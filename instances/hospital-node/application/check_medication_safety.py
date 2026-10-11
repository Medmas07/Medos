"""Check a proposed medication against current medications (HC-162).

The caller sends the authorized medication history it already holds; this node does not
fetch it, store it, or read its own clinical repository for the check. The rule set
comes through the InteractionRuleSource port. When no rule set is available, or the
proposed medication cannot be identified, no check is performed: callers must show
that, never "no warnings".

An optional WarningExplainer (HC-164) adds an advisory explanation to each warning
after the deterministic check has produced it. It never creates, removes, or changes a
warning. When it is absent or fails, the warning's explanation is null and the warning
is complete without it.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from domain.medication_safety import (
    CheckOutcome,
    InteractionWarning,
    Medication,
    MedicationStatement,
    ProposedMedicationNotEvaluable,
    RuleSet,
    SafetySourceKind,
    check_interactions,
)

ENGINE_NAME = "hospital-node-interaction-engine"
ENGINE_VERSION = "hc-162-v1"


def warning_id(index: int) -> str:
    """The id of the warning at `index` (from 0) in a result."""
    return f"warning-{index + 1}"


class ExplanationUnavailable(Exception):
    """No usable explanation; the warning keeps a null explanation."""


@dataclass(frozen=True)
class WarningExplanation:
    """medication-safety-check.v1.yaml's Explanation: advisory, never the safety source."""

    text: str
    generator_kind: str  # "model" or "deterministic_template"
    generator_name: str
    generator_version: str
    generator_mocked: bool
    generated_at: str


class WarningExplainer(Protocol):
    def explain(
        self,
        warning_id: str,
        warning: InteractionWarning,
        rules: RuleSet,
        requested_by: str,
    ) -> WarningExplanation: ...


class RuleSourceUnavailable(Exception):
    pass


class CheckNotPerformed(Exception):
    """No check was performed; the reason is safe to show the caller."""


class InteractionRuleSource(Protocol):
    # True when the rules are fixtures rather than a real rule source.
    mocked: bool

    def rule_set(self) -> RuleSet: ...


@dataclass(frozen=True)
class SafetyCheckRequest:
    patient_ref: str
    requested_by: str
    proposed_medication: Medication
    current_medications: tuple[MedicationStatement, ...]
    encounter_ref: str | None = None


@dataclass(frozen=True)
class Engine:
    kind: SafetySourceKind
    name: str
    version: str


@dataclass(frozen=True)
class SafetyCheckResult:
    check_id: str
    request: SafetyCheckRequest
    outcome: CheckOutcome
    rule_set: RuleSet
    engine: Engine
    mocked: bool
    evaluated_at: datetime
    # One per warning, in order; None when no explanation was produced.
    explanations: tuple[WarningExplanation | None, ...] = ()


class CheckMedicationSafety:
    def __init__(
        self,
        rule_source: InteractionRuleSource,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
        explainer: WarningExplainer | None = None,
    ) -> None:
        self._rule_source = rule_source
        self._clock = clock
        self._new_id = new_id
        self._explainer = explainer

    def __call__(self, request: SafetyCheckRequest) -> SafetyCheckResult:
        try:
            rules = self._rule_source.rule_set()
        except RuleSourceUnavailable as error:
            raise CheckNotPerformed(
                "The rule source is unavailable. No check was performed."
            ) from error
        try:
            outcome = check_interactions(
                rules, request.proposed_medication, request.current_medications
            )
        except ProposedMedicationNotEvaluable as error:
            raise CheckNotPerformed(
                "The rule source cannot evaluate the proposed medication "
                f"({error.reason.value}). No check was performed."
            ) from error
        return SafetyCheckResult(
            explanations=self._explanations(outcome, rules, request.requested_by),
            check_id=self._new_id(),
            request=request,
            outcome=outcome,
            rule_set=rules,
            engine=Engine(rules.kind, ENGINE_NAME, ENGINE_VERSION),
            mocked=self._rule_source.mocked,
            evaluated_at=self._clock(),
        )

    def _explanations(
        self, outcome: CheckOutcome, rules: RuleSet, requested_by: str
    ) -> tuple[WarningExplanation | None, ...]:
        explainer = self._explainer
        if explainer is None or not outcome.warnings:
            return tuple(None for _ in outcome.warnings)

        def explain(item: tuple[int, InteractionWarning]) -> WarningExplanation | None:
            index, warning = item
            try:
                return explainer.explain(
                    warning_id(index), warning, rules, requested_by
                )
            except ExplanationUnavailable:
                return None

        # Each explanation may take seconds (a model call): ask for them in parallel.
        with ThreadPoolExecutor(max_workers=min(4, len(outcome.warnings))) as pool:
            return tuple(pool.map(explain, enumerate(outcome.warnings)))
