"""Research access request use cases (HC-133) and the ports they own."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from application.hospital_approval import HospitalApplicationStore, ReviewerDirectory
from domain.hospital_application import ApplicationStatus
from domain.research import (
    AuthorizationAnswer,
    Check,
    JobAsk,
    RequestStatus,
    ResearchDecision,
    ResearchDecisionDraft,
    ResearchRequest,
    check_authorization,
    checks,
    decide,
    eligible_organizations,
    status_at,
)

_STATUS_ORDER = tuple(RequestStatus)


class RequestNotFound(Exception):
    pass


class DecisionNotFound(Exception):
    pass


class ResearchStore(Protocol):
    def requests(self) -> list[ResearchRequest]: ...

    def request(self, request_ref: str) -> ResearchRequest | None: ...

    def decision(self, decision_ref: str) -> ResearchDecision | None: ...

    def submit(self, new_request: Callable[[str], ResearchRequest]) -> ResearchRequest:
        """Store the request built with the next free reference, and return it. The
        builder runs while the store is locked and must not call the store."""
        ...

    def record(self, decided: ResearchRequest, decision: ResearchDecision) -> None:
        """Store both at once; raise NotUnderReview if the request was decided in the
        meantime."""
        ...


@dataclass(frozen=True)
class RequestView:
    request: ResearchRequest
    decision: ResearchDecision | None
    status: RequestStatus
    # Evaluated when answering; informative once decided.
    checks: list[Check]
    eligible_organization_refs: tuple[str, ...]


def _approved_organizations(applications: HospitalApplicationStore) -> frozenset[str]:
    # Organizations approved by this Node's own hospital approval decisions (HC-131).
    return frozenset(
        a.organization_ref
        for a in applications.applications()
        if a.status is ApplicationStatus.APPROVED
    )


def _decision_of(
    request: ResearchRequest, store: ResearchStore
) -> ResearchDecision | None:
    return store.decision(request.decision_ref) if request.decision_ref else None


def list_requests(
    store: ResearchStore, now: datetime, status: RequestStatus | None = None
) -> list[tuple[ResearchRequest, ResearchDecision | None, RequestStatus]]:
    rows = []
    for request in store.requests():
        decision = _decision_of(request, store)
        row_status = status_at(decision, now)
        if status in (None, row_status):
            rows.append((request, decision, row_status))
    # Newest first, then stable by status group.
    rows.sort(key=lambda row: row[0].submitted_at, reverse=True)
    rows.sort(key=lambda row: _STATUS_ORDER.index(row[2]))
    return rows


def get_request(
    request_ref: str,
    store: ResearchStore,
    applications: HospitalApplicationStore,
    clock: Callable[[], datetime],
) -> RequestView:
    request = store.request(request_ref)
    if request is None:
        raise RequestNotFound(request_ref)
    approved = _approved_organizations(applications)
    decision = _decision_of(request, store)
    return RequestView(
        request,
        decision,
        status_at(decision, clock()),
        checks(request, approved),
        eligible_organizations(request, approved),
    )


def submit_request(
    build: Callable[[str, datetime], ResearchRequest],
    store: ResearchStore,
    clock: Callable[[], datetime],
) -> ResearchRequest:
    """Record a request under review. `build` gets the new reference and the time,
    and raises InvalidResearchRequest."""
    now = clock()
    return store.submit(lambda request_ref: build(request_ref, now))


def decide_request(
    request_ref: str,
    reviewer_ref: str,
    draft: ResearchDecisionDraft,
    store: ResearchStore,
    reviewers: ReviewerDirectory,
    applications: HospitalApplicationStore,
    clock: Callable[[], datetime],
) -> ResearchDecision:
    request = store.request(request_ref)
    if request is None:
        raise RequestNotFound(request_ref)
    decision, decided = decide(
        request,
        _decision_of(request, store),
        reviewers.reviewer(reviewer_ref),
        draft,
        _approved_organizations(applications),
        clock(),
    )
    store.record(decided, decision)
    return decision


def check_research_authorization(
    decision_ref: str, ask: JobAsk, store: ResearchStore, clock: Callable[[], datetime]
) -> AuthorizationAnswer:
    """Raises DecisionNotFound for an unknown reference or another subject's decision."""
    decision = store.decision(decision_ref)
    request = store.request(decision.request_ref) if decision else None
    if decision is None or request is None:
        raise DecisionNotFound(decision_ref)
    return check_authorization(decision, request, ask, clock())
