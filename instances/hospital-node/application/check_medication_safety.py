"""Check a proposed medication against current medications (HC-162).

The caller sends the authorized medication history it already holds; this node does not
fetch it, store it, or read its own clinical repository for the check. The rule set
comes through the InteractionRuleSource port. When no rule set is available, or the
proposed medication cannot be identified, no check is performed: callers must show
that, never "no warnings".
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from domain.medication_safety import (
    CheckOutcome,
    Medication,
    MedicationStatement,
    ProposedMedicationNotEvaluable,
    RuleSet,
    SafetySourceKind,
    check_interactions,
)

ENGINE_NAME = "hospital-node-interaction-engine"
ENGINE_VERSION = "hc-162-v1"


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


class CheckMedicationSafety:
    def __init__(
        self,
        rule_source: InteractionRuleSource,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._rule_source = rule_source
        self._clock = clock
        self._new_id = new_id

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
            check_id=self._new_id(),
            request=request,
            outcome=outcome,
            rule_set=rules,
            engine=Engine(rules.kind, ENGINE_NAME, ENGINE_VERSION),
            mocked=self._rule_source.mocked,
            evaluated_at=self._clock(),
        )
