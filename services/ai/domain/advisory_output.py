from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ReviewState(Enum):
    # Every AI output starts unconfirmed. Review outcomes arrive with the review workflow (HC-152+).
    PENDING_HUMAN_REVIEW = "pending_human_review"


@dataclass(frozen=True)
class Provenance:
    provider_id: str
    model_id: str
    is_mock: bool
    generated_at: datetime


@dataclass(frozen=True)
class AdvisoryOutput:
    """Advisory AI output. It never becomes clinical truth without human review."""

    text: str
    provenance: Provenance
    uncertainty_notes: tuple[str, ...] = ()
    review_state: ReviewState = ReviewState.PENDING_HUMAN_REVIEW
