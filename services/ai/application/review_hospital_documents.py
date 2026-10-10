"""Review a hospital onboarding dossier (HC-154): the use case and the port it owns."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from domain.document_review import (
    Dossier,
    DocumentReview,
    ReviewerInfo,
    ReviewFinding,
    verified,
)


@dataclass(frozen=True)
class ReviewerOutput:
    findings: tuple[ReviewFinding, ...]
    reviewer: ReviewerInfo
    uncertainty_notes: tuple[str, ...] = ()
    # Proposals the reviewer could not even express as a finding: no citation at all.
    uncited: int = 0


class ReviewUnavailable(Exception):
    """No reviewer could produce a usable review. Maps to 503 in the contract."""


class DocumentReviewer(Protocol):
    """Whatever proposes findings on a dossier: fixtures or a model."""

    def review(self, dossier: Dossier) -> ReviewerOutput: ...


@dataclass(frozen=True)
class ReviewRequest:
    application_ref: str
    requested_by: str
    dossier: Dossier


class ReviewHospitalDocuments:
    """Every finding is checked against the dossier here, whatever the reviewer: one
    citing nothing that exists is dropped and counted, never shown."""

    def __init__(
        self,
        reviewer: DocumentReviewer,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._reviewer = reviewer
        self._clock = clock
        self._new_id = new_id

    def __call__(self, request: ReviewRequest) -> DocumentReview:
        output = self._reviewer.review(request.dossier)
        kept = []
        for finding in output.findings:
            checked = verified(finding, request.dossier)
            if checked is not None:
                kept.append(checked)
        findings = tuple(
            ReviewFinding(
                f"finding-{number}",
                f.category,
                f.message,
                f.field_paths,
                f.evidence,
            )
            for number, f in enumerate(kept, start=1)
        )
        return DocumentReview(
            review_id=self._new_id(),
            application_ref=request.application_ref,
            requested_by=request.requested_by,
            findings=findings,
            unverified_findings_dropped=output.uncited
            + len(output.findings)
            - len(kept),
            reviewer=output.reviewer,
            generated_at=self._clock(),
            uncertainty_notes=output.uncertainty_notes,
        )
