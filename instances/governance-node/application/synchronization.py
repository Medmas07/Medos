"""Synchronization request use cases (HC-132) and the ports they own."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from application.hospital_approval import HospitalApplicationStore, ReviewerDirectory
from domain.hospital_application import ApplicationStatus
from domain.synchronization import (
    AuthorizationCheck,
    Check,
    Consent,
    ExchangeAsk,
    PatientGrant,
    RequestStatus,
    ReviewContext,
    ScopeItem,
    SyncDecisionDraft,
    SynchronizationDecision,
    SynchronizationRequest,
    check_authorization,
    checks,
    decide,
    max_approved_days,
    status_at,
)

_STATUS_ORDER = tuple(RequestStatus)


class RequestNotFound(Exception):
    pass


class SynchronizationStore(Protocol):
    def requests(self) -> list[SynchronizationRequest]: ...

    def request(self, request_ref: str) -> SynchronizationRequest | None: ...

    def decision(self, decision_ref: str) -> SynchronizationDecision | None: ...

    def submit(
        self, new_request: Callable[[str], SynchronizationRequest]
    ) -> SynchronizationRequest:
        """Store the request built with the next free reference, and return it."""
        ...

    def record(
        self, decided: SynchronizationRequest, decision: SynchronizationDecision
    ) -> None:
        """Store both at once; raise NotPending if the request was decided in the
        meantime."""
        ...


class PatientGrantDirectory(Protocol):
    def grant(self, grant_ref: str) -> PatientGrant | None: ...


@dataclass(frozen=True)
class RequestView:
    request: SynchronizationRequest
    decision: SynchronizationDecision | None
    status: RequestStatus
    # Evaluated when answering; informative once decided.
    checks: list[Check]
    max_approved_days: int


def _decision_of(
    request: SynchronizationRequest, store: SynchronizationStore
) -> SynchronizationDecision | None:
    return store.decision(request.decision_ref) if request.decision_ref else None


def _context(
    request: SynchronizationRequest,
    grants: PatientGrantDirectory,
    applications: HospitalApplicationStore,
    now: datetime,
) -> ReviewContext:
    # Organizations approved by this Node's own hospital approval decisions (HC-131).
    approved = frozenset(
        a.organization_ref
        for a in applications.applications()
        if a.status is ApplicationStatus.APPROVED
    )
    ref = request.consent.access_grant_ref
    return ReviewContext(approved, grants.grant(ref) if ref else None, now)


def list_requests(
    store: SynchronizationStore, now: datetime, status: RequestStatus | None = None
) -> list[tuple[SynchronizationRequest, SynchronizationDecision | None, RequestStatus]]:
    rows = []
    for request in store.requests():
        decision = _decision_of(request, store)
        row_status = status_at(request, decision, now)
        if status in (None, row_status):
            rows.append((request, decision, row_status))
    # Newest first, then stable by status group.
    rows.sort(key=lambda row: row[0].submitted_at, reverse=True)
    rows.sort(key=lambda row: _STATUS_ORDER.index(row[2]))
    return rows


def get_request(
    request_ref: str,
    store: SynchronizationStore,
    grants: PatientGrantDirectory,
    applications: HospitalApplicationStore,
    clock: Callable[[], datetime],
) -> RequestView:
    request = store.request(request_ref)
    if request is None:
        raise RequestNotFound(request_ref)
    now = clock()
    context = _context(request, grants, applications, now)
    decision = _decision_of(request, store)
    return RequestView(
        request,
        decision,
        status_at(request, decision, now),
        checks(request, context),
        max_approved_days(request, context),
    )


def submit_request(
    requester_organization_ref: str,
    submitted_by_ref: str,
    target_organization_ref: str,
    patient_ref: str,
    purpose: str,
    scope: frozenset[ScopeItem],
    duration_days: int,
    consent: Consent,
    store: SynchronizationStore,
    clock: Callable[[], datetime],
) -> SynchronizationRequest:
    """Record a pending request. Raises InvalidSynchronizationRequest."""
    now = clock()
    return store.submit(
        lambda request_ref: SynchronizationRequest(
            request_ref=request_ref,
            requester_organization_ref=requester_organization_ref,
            target_organization_ref=target_organization_ref,
            patient_ref=patient_ref,
            purpose=purpose.strip(),
            scope=scope,
            duration_days=duration_days,
            consent=consent,
            submitted_at=now,
            submitted_by_ref=submitted_by_ref,
        )
    )


def decide_request(
    request_ref: str,
    reviewer_ref: str,
    draft: SyncDecisionDraft,
    store: SynchronizationStore,
    reviewers: ReviewerDirectory,
    grants: PatientGrantDirectory,
    applications: HospitalApplicationStore,
    clock: Callable[[], datetime],
) -> SynchronizationDecision:
    request = store.request(request_ref)
    if request is None:
        raise RequestNotFound(request_ref)
    decision, decided = decide(
        request,
        _decision_of(request, store),
        reviewers.reviewer(reviewer_ref),
        draft,
        _context(request, grants, applications, clock()),
    )
    store.record(decided, decision)
    return decision


def check_sync_authorization(
    decision_ref: str,
    ask: ExchangeAsk,
    store: SynchronizationStore,
    clock: Callable[[], datetime],
) -> AuthorizationCheck:
    decision = store.decision(decision_ref)
    request = store.request(decision.request_ref) if decision else None
    found = (decision, request) if decision and request else None
    return check_authorization(decision_ref, found, ask, clock())
