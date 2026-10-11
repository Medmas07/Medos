"""Explain a priority queue entry (HC-157): the use case and its port.

The explainer only proposes text. Model text is shown only if it passes the guardrails
of domain/priority_explanation.py; otherwise, and whenever no model answers, the
deterministic template is returned, with the reasons. The explanation is always
advisory; the rank and the priority stay those of the priority method.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from application.explanation import ExplanationUnavailable, ProposedExplanation
from domain.explanation import Explanation, GeneratedBy, GeneratorKind
from domain.priority_explanation import (
    QueueEntry,
    displayed_text,
    guardrail_problems,
    template_text,
)

TEMPLATE = GeneratedBy(
    kind=GeneratorKind.DETERMINISTIC_TEMPLATE,
    name="priority-queue-template",
    version="hc-157-v1",
    mocked=False,
)


class PriorityExplainer(Protocol):
    def explain(self, entry: QueueEntry) -> ProposedExplanation: ...


@dataclass(frozen=True)
class PriorityExplanationResult:
    explanation_id: str
    entry_id: str
    explanation: Explanation
    # Why model text was not used; empty when it was, or when none was asked for.
    rejected_reasons: tuple[str, ...]
    uncertainty_notes: tuple[str, ...]


class TemplatePriorityExplainer:
    """No model: the deterministic template only."""

    def explain(self, entry: QueueEntry) -> ProposedExplanation:
        return ProposedExplanation(template_text(entry), TEMPLATE)


class ExplainPriorityEntry:
    def __init__(
        self,
        explainer: PriorityExplainer,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._explainer = explainer
        self._clock = clock
        self._new_id = new_id

    def __call__(self, entry: QueueEntry) -> PriorityExplanationResult:
        rejected: tuple[str, ...] = ()
        notes: tuple[str, ...] = ()
        try:
            proposed = self._explainer.explain(entry)
        except ExplanationUnavailable as error:
            proposed = None
            rejected = (f"no model explanation: {error}",)
        if proposed is not None and proposed.generated_by.kind is GeneratorKind.MODEL:
            problems = guardrail_problems(proposed.text, entry)
            if problems:
                rejected, proposed = tuple(problems), None
            else:
                notes = proposed.uncertainty_notes
        if proposed is None:
            proposed = ProposedExplanation(template_text(entry), TEMPLATE)
            notes = ("Deterministic template: no model text is shown.",)
        return PriorityExplanationResult(
            explanation_id=self._new_id(),
            entry_id=entry.entry_id,
            explanation=Explanation(
                text=displayed_text(proposed.text),
                generated_by=proposed.generated_by,
                generated_at=self._clock(),
            ),
            rejected_reasons=rejected,
            uncertainty_notes=notes,
        )
