"""Hospital approval use cases (HC-131) and the ports they own."""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from application.audit import AUTHORITY_ORGANIZATION_REF, AuditTrail, record
from application.ledger import AuditLedgerPort, anchor_recorded
from domain.audit import AuditAction, AuditDomain, AuditOutcome, SubjectType
from domain.hospital_application import ApplicationStatus, HospitalApplication
from domain.hospital_approval import (
    DecisionDraft,
    HospitalApprovalDecision,
    Reviewer,
    decide,
)
from domain.policy import PolicyHistory

# Awaiting a human first, then still being checked, then decided.
_STATUS_ORDER = (
    ApplicationStatus.HUMAN_REVIEW,
    ApplicationStatus.PENDING,
    ApplicationStatus.APPROVED,
    ApplicationStatus.REJECTED,
)


class ApplicationNotFound(Exception):
    pass


class HospitalApplicationStore(Protocol):
    def applications(self) -> list[HospitalApplication]: ...

    def application(self, application_ref: str) -> HospitalApplication | None: ...

    def decision(self, decision_ref: str) -> HospitalApprovalDecision | None: ...

    def record(
        self, decided: HospitalApplication, decision: HospitalApprovalDecision
    ) -> None:
        """Store both at once; raise NotAwaitingReview if the application was decided
        in the meantime."""
        ...


class ReviewerDirectory(Protocol):
    def reviewer(self, person_ref: str) -> Reviewer | None: ...


def list_applications(
    store: HospitalApplicationStore, status: ApplicationStatus | None = None
) -> list[HospitalApplication]:
    selected = [a for a in store.applications() if status in (None, a.status)]
    # Newest first, then stable by status group.
    selected.sort(key=lambda a: a.submitted_at, reverse=True)
    selected.sort(key=lambda a: _STATUS_ORDER.index(a.status))
    return selected


def get_application(
    application_ref: str, store: HospitalApplicationStore
) -> tuple[HospitalApplication, HospitalApprovalDecision | None]:
    application = store.application(application_ref)
    if application is None:
        raise ApplicationNotFound(application_ref)
    decision = (
        store.decision(application.decision_ref) if application.decision_ref else None
    )
    return application, decision


def decide_application(
    application_ref: str,
    reviewer_ref: str,
    draft: DecisionDraft,
    store: HospitalApplicationStore,
    reviewers: ReviewerDirectory,
    policies: PolicyHistory,
    audit: AuditTrail,
    clock: Callable[[], datetime],
    ledger: AuditLedgerPort | None = None,
) -> HospitalApprovalDecision:
    """Decided under the governance policy in effect now, which it cites."""
    application = store.application(application_ref)
    if application is None:
        raise ApplicationNotFound(application_ref)
    now = clock()
    decision, decided = decide(
        application,
        reviewers.reviewer(reviewer_ref),
        draft,
        policies.in_effect(now),
        now,
    )
    store.record(decided, decision)
    event = record(
        audit,
        decision.decided_at,
        AuditAction.DECISION_RECORDED,
        AuditDomain.HOSPITAL_APPROVAL,
        decision.decided_by_ref,
        SubjectType.DECISION,
        decision.decision_ref,
        (AUTHORITY_ORGANIZATION_REF, decision.organization_ref),
        AuditOutcome(decision.outcome.value),
    )
    # HC-191: anchored in the ledger, if any; the decision stands either way.
    anchor_recorded(ledger, event)
    return decision


def get_hospital_approval(
    decision_ref: str, store: HospitalApplicationStore
) -> HospitalApprovalDecision | None:
    return store.decision(decision_ref)
