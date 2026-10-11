"""Research access request use cases (HC-133) and the ports they own."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from application.audit import AUTHORITY_ORGANIZATION_REF, AuditTrail, record
from application.hospital_approval import HospitalApplicationStore, ReviewerDirectory
from application.ledger import AuditLedgerPort, anchor_recorded
from domain.audit import AuditAction, AuditDomain, AuditOutcome, SubjectType
from domain.hospital_application import ApplicationStatus
from domain.policy import PolicyHistory
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


def _organizations(request: ResearchRequest) -> tuple[str, ...]:
    return (request.research_organization_ref, *request.participating_organization_refs)


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
    audit: AuditTrail,
    clock: Callable[[], datetime],
) -> ResearchRequest:
    """Record a request under review. `build` gets the new reference and the time,
    and raises InvalidResearchRequest."""
    now = clock()
    request = store.submit(lambda request_ref: build(request_ref, now))
    record(
        audit,
        now,
        AuditAction.REQUEST_RECEIVED,
        AuditDomain.RESEARCH,
        request.submitted_by_ref,
        SubjectType.RESEARCH_ACCESS_REQUEST,
        request.request_ref,
        _organizations(request),
    )
    return request


def decide_request(
    request_ref: str,
    reviewer_ref: str,
    draft: ResearchDecisionDraft,
    store: ResearchStore,
    reviewers: ReviewerDirectory,
    applications: HospitalApplicationStore,
    policies: PolicyHistory,
    audit: AuditTrail,
    clock: Callable[[], datetime],
    ledger: AuditLedgerPort | None = None,
) -> ResearchDecision:
    """Decided under the governance policy in effect now, which it cites."""
    request = store.request(request_ref)
    if request is None:
        raise RequestNotFound(request_ref)
    now = clock()
    decision, decided = decide(
        request,
        _decision_of(request, store),
        reviewers.reviewer(reviewer_ref),
        draft,
        _approved_organizations(applications),
        policies.in_effect(now),
        now,
    )
    store.record(decided, decision)
    event = record(
        audit,
        decision.decided_at,
        AuditAction.DECISION_RECORDED,
        AuditDomain.RESEARCH,
        decision.decided_by_ref,
        SubjectType.DECISION,
        decision.decision_ref,
        (AUTHORITY_ORGANIZATION_REF, *_organizations(request)),
        AuditOutcome(decision.outcome.value),
    )
    # HC-191: anchored in the ledger, if any; the decision stands either way.
    anchor_recorded(ledger, event)
    return decision


def check_research_authorization(
    decision_ref: str,
    ask: JobAsk,
    store: ResearchStore,
    audit: AuditTrail,
    clock: Callable[[], datetime],
) -> AuthorizationAnswer:
    """Raises DecisionNotFound for an unknown reference or another subject's decision,
    which is not audited. An answer is recorded before it is given: no audit, no
    answer."""
    decision = store.decision(decision_ref)
    request = store.request(decision.request_ref) if decision else None
    if decision is None or request is None:
        raise DecisionNotFound(decision_ref)
    now = clock()
    answer = check_authorization(decision, request, ask, now)
    record(
        audit,
        now,
        AuditAction.AUTHORIZATION_CHECKED,
        AuditDomain.RESEARCH,
        ask.requested_by,
        SubjectType.DECISION,
        decision_ref,
        (AUTHORITY_ORGANIZATION_REF, *sorted(ask.target_organization_refs)),
        AuditOutcome.AUTHORIZED if answer.approved else AuditOutcome.DENIED,
        answer.reason.value if answer.reason else None,
    )
    return answer
