"""A hospital's application to join the ecosystem, as the Governance Node reviews it."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# An application reference: "app-" and an opaque suffix, so that its decision reference
# ("dec-" and the same suffix) is an opaque reference too.
_APPLICATION_REF = re.compile(r"app-[A-Za-z0-9._:-]{1,124}")
_OPAQUE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


class InvalidHospitalApplication(ValueError):
    pass


class ApplicationStatus(str, Enum):
    PENDING = "pending"  # submitted, automated checks not finished
    HUMAN_REVIEW = "human_review"  # awaiting a reviewer's decision
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class MissingDocument:
    document_ref: str
    type: str
    title: str


@dataclass(frozen=True)
class Findings:
    """What a reviewer must examine before deciding."""

    missing_documents: tuple[MissingDocument, ...] = ()
    unaccepted_agreements: tuple[str, ...] = ()
    # Deterministic completeness check.
    completeness_findings: tuple[str, ...] = ()
    # Assisted (AI) review: advisory, never binding.
    advisory_findings: tuple[str, ...] = ()

    @property
    def count(self) -> int:
        return (
            len(self.missing_documents)
            + len(self.unaccepted_agreements)
            + len(self.completeness_findings)
            + len(self.advisory_findings)
        )

    @property
    def incomplete(self) -> bool:
        """Documents or agreements are missing: an approval needs conditions."""
        return bool(self.missing_documents or self.unaccepted_agreements)


@dataclass(frozen=True)
class HospitalApplication:
    application_ref: str
    organization_ref: str
    status: ApplicationStatus
    submitted_at: datetime
    findings: Findings
    decision_ref: str | None = None

    def __post_init__(self) -> None:
        if not _APPLICATION_REF.fullmatch(self.application_ref):
            raise InvalidHospitalApplication(
                "application_ref must be 'app-' and an opaque suffix"
            )
        if not _OPAQUE_REF.fullmatch(self.organization_ref):
            raise InvalidHospitalApplication(
                "organization_ref must be an opaque reference"
            )
        if self.submitted_at.tzinfo is None:
            raise InvalidHospitalApplication("submitted_at must carry a UTC offset")
        decided = self.status in (
            ApplicationStatus.APPROVED,
            ApplicationStatus.REJECTED,
        )
        if decided != (self.decision_ref is not None):
            raise InvalidHospitalApplication(
                "an application has a decision exactly when it is approved or rejected"
            )

    @property
    def awaiting_review(self) -> bool:
        return self.status is ApplicationStatus.HUMAN_REVIEW

    @property
    def decision_ref_to_record(self) -> str:
        """The reference its decision gets: one decision per application."""
        return "dec-" + self.application_ref.removeprefix("app-")
