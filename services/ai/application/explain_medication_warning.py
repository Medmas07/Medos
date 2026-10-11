"""Explain a deterministic medication warning (HC-156): the use case and its port.

The explainer only proposes text. Model text is shown only if it passes the guardrails
of domain/medication_explanation.py; otherwise, and whenever no model answers, the
deterministic template is returned, with the reasons. The explanation is always
advisory, and the warning stays complete without it.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from application.explanation import ExplanationUnavailable, ProposedExplanation
from domain.explanation import Explanation, GeneratedBy, GeneratorKind
from domain.medication_explanation import (
    MedicationWarning,
    guardrail_problems,
    template_text,
)

TEMPLATE = GeneratedBy(
    kind=GeneratorKind.DETERMINISTIC_TEMPLATE,
    name="medication-warning-template",
    version="hc-156-v1",
    mocked=False,
)


class WarningExplainer(Protocol):
    def explain(self, warning: MedicationWarning) -> ProposedExplanation: ...


@dataclass(frozen=True)
class ExplanationResult:
    explanation_id: str
    warning_id: str
    explanation: Explanation
    # Why model text was not used; empty when it was, or when none was asked for.
    rejected_reasons: tuple[str, ...]
    uncertainty_notes: tuple[str, ...]


class TemplateExplainer:
    """No model: the deterministic template only."""

    def explain(self, warning: MedicationWarning) -> ProposedExplanation:
        return ProposedExplanation(template_text(warning), TEMPLATE)


class ExplainMedicationWarning:
    def __init__(
        self,
        explainer: WarningExplainer,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._explainer = explainer
        self._clock = clock
        self._new_id = new_id

    def __call__(self, warning: MedicationWarning) -> ExplanationResult:
        rejected: tuple[str, ...] = ()
        notes: tuple[str, ...] = ()
        try:
            proposed = self._explainer.explain(warning)
        except ExplanationUnavailable as error:
            proposed = None
            rejected = (f"no model explanation: {error}",)
        if proposed is not None and proposed.generated_by.kind is GeneratorKind.MODEL:
            problems = guardrail_problems(proposed.text, warning)
            if problems:
                rejected, proposed = tuple(problems), None
            else:
                notes = proposed.uncertainty_notes
        if proposed is None:
            proposed = ProposedExplanation(template_text(warning), TEMPLATE)
            notes = ("Deterministic template: no model text is shown.",)
        return ExplanationResult(
            explanation_id=self._new_id(),
            warning_id=warning.warning_id,
            explanation=Explanation(
                text=proposed.text.strip(),
                generated_by=proposed.generated_by,
                generated_at=self._clock(),
            ),
            rejected_reasons=rejected,
            uncertainty_notes=notes,
        )
