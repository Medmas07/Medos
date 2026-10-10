"""LLM-assisted review of a hospital onboarding dossier (HC-154).

The optional review step of hospital onboarding (product vision §4): between the
deterministic completeness check and human review by the Governance / Ethics Authority.
It only points out what a reviewer should look at: inconsistencies, missing information,
and points to clarify. It never approves, rejects, or scores an application, and every
finding must cite the dossier: field paths that exist, or a quote found verbatim in a
document's text. The dossier is administrative and technical, never clinical.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

MAX_FIELDS = 200
MAX_FIELD_VALUE_LENGTH = 500
MAX_DOCUMENTS = 10
MAX_DOCUMENT_TEXT_LENGTH = 20_000
_FIELD_PATH = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")
_OPAQUE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

FieldValue = str | int | float | bool | None


class InvalidDossier(ValueError):
    pass


class FindingCategory(Enum):
    INCONSISTENCY = "inconsistency"
    MISSING_INFORMATION = "missing_information"
    CLARIFICATION_NEEDED = "clarification_needed"


class ReviewerKind(Enum):
    MODEL = "model"
    DETERMINISTIC_FIXTURE = "deterministic_fixture"


class ReviewStatus(Enum):
    # A review only informs the human reviewer; nothing here confirms or decides.
    PENDING_HUMAN_REVIEW = "pending_human_review"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidDossier(message)


@dataclass(frozen=True)
class DossierField:
    """One answer of the dossier, by its path, for example
    `administrative_profile.security_contact`."""

    path: str
    value: FieldValue

    def __post_init__(self) -> None:
        _require(
            bool(_FIELD_PATH.fullmatch(self.path)) and len(self.path) <= 200,
            f"field path {self.path!r} must be lower-case dotted segments",
        )
        _require(
            not isinstance(self.value, str)
            or len(self.value) <= MAX_FIELD_VALUE_LENGTH,
            f"{self.path}: value longer than {MAX_FIELD_VALUE_LENGTH} characters",
        )


@dataclass(frozen=True)
class DossierDocument:
    """A supporting document's metadata and, when the caller has it, its text."""

    document_ref: str
    type: str
    title: str
    status: str
    text: str | None = None

    def __post_init__(self) -> None:
        _require(
            bool(_OPAQUE_REF.fullmatch(self.document_ref)),
            "document_ref must be opaque",
        )
        for field in ("type", "title", "status"):
            value = getattr(self, field)
            _require(
                0 < len(value) <= 200, f"document {field} must be 1-200 characters"
            )
        _require(
            self.text is None or 0 < len(self.text) <= MAX_DOCUMENT_TEXT_LENGTH,
            f"document text must be 1-{MAX_DOCUMENT_TEXT_LENGTH} characters",
        )


@dataclass(frozen=True)
class Dossier:
    fields: tuple[DossierField, ...]
    documents: tuple[DossierDocument, ...] = ()

    def __post_init__(self) -> None:
        _require(0 < len(self.fields) <= MAX_FIELDS, f"1-{MAX_FIELDS} fields")
        paths = [f.path for f in self.fields]
        _require(len(set(paths)) == len(paths), "field paths must be unique")
        _require(
            len(self.documents) <= MAX_DOCUMENTS, f"at most {MAX_DOCUMENTS} documents"
        )
        refs = [d.document_ref for d in self.documents]
        _require(len(set(refs)) == len(refs), "document refs must be unique")

    def has_field(self, path: str) -> bool:
        return any(f.path == path for f in self.fields)

    def document(self, document_ref: str) -> DossierDocument | None:
        return next((d for d in self.documents if d.document_ref == document_ref), None)


@dataclass(frozen=True)
class DocumentQuote:
    """Verbatim text from one of the dossier's documents."""

    document_ref: str
    quote: str


@dataclass(frozen=True)
class ReviewFinding:
    finding_id: str
    category: FindingCategory
    message: str
    field_paths: tuple[str, ...]
    evidence: DocumentQuote | None = None

    def __post_init__(self) -> None:
        _require(bool(self.message.strip()), "a finding has a message")
        _require(
            bool(self.field_paths) or self.evidence is not None,
            "a finding cites at least one field or a document quote",
        )


@dataclass(frozen=True)
class ReviewerInfo:
    kind: ReviewerKind
    name: str
    version: str
    mocked: bool


@dataclass(frozen=True)
class DocumentReview:
    review_id: str
    application_ref: str
    requested_by: str
    findings: tuple[ReviewFinding, ...]
    # Findings the reviewer proposed but that cited nothing in the dossier.
    unverified_findings_dropped: int
    reviewer: ReviewerInfo
    generated_at: datetime
    uncertainty_notes: tuple[str, ...] = ()
    advisory: bool = True
    review_status: ReviewStatus = ReviewStatus.PENDING_HUMAN_REVIEW


def verified(finding: ReviewFinding, dossier: Dossier) -> ReviewFinding | None:
    """The finding with only the citations the dossier supports, or None if none is.

    A field path must exist in the dossier. A quote must be found in that document's
    text, exactly or ignoring case only; the dossier's own characters are kept."""
    paths = tuple(p for p in dict.fromkeys(finding.field_paths) if dossier.has_field(p))
    evidence = None
    if finding.evidence is not None:
        document = dossier.document(finding.evidence.document_ref)
        quote = finding.evidence.quote.strip()
        if document is not None and document.text and quote:
            start = document.text.find(quote)
            if start < 0:
                start = document.text.lower().find(quote.lower())
            if start >= 0:
                evidence = DocumentQuote(
                    document.document_ref, document.text[start : start + len(quote)]
                )
    if not paths and evidence is None:
        return None
    return ReviewFinding(
        finding.finding_id, finding.category, finding.message.strip(), paths, evidence
    )
