"""Synchronization request use cases (HC-132) and the ports they own."""

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
    relies_on_patient_grant,
    reverify_consent,
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
        """Store the request built with the next free reference, and return it. The
        builder runs while the store is locked and must not call the store."""
        ...

    def record(
        self, decided: SynchronizationRequest, decision: SynchronizationDecision
    ) -> None:
        """Store both at once; raise NotPending if the request was decided in the
        meantime."""
        ...


class GrantsUnavailable(Exception):
    """The Hospital Node holding the grant could not answer within the contract."""


class PatientGrantDirectory(Protocol):
    # Where grants come from, reported by /health: "http" (the Hospital Nodes) or
    # "fixture" (MOCKED seed grants).
    mode: str

    def grant(
        self, holder_organization_ref: str, patient_ref: str, grant_ref: str
    ) -> PatientGrant | None:
        """The patient's grant as the holder organization's Hospital Node records it
        now; None if that node does not know it for this patient. Raises
        GrantsUnavailable when the node cannot be asked or answers outside
        patient-access-grants.v1.yaml."""
        ...


def _lookup_grant(
    request: SynchronizationRequest, grants: PatientGrantDirectory
) -> PatientGrant | None:
    # The target organization holds the records exchanged and enforces the grant.
    return grants.grant(
        request.target_organization_ref,
        request.patient_ref,
        request.consent.access_grant_ref,
    )


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
    policies: PolicyHistory,
    now: datetime,
) -> ReviewContext:
    # Organizations approved by this Node's own hospital approval decisions (HC-131).
    approved = frozenset(
        a.organization_ref
        for a in applications.applications()
        if a.status is ApplicationStatus.APPROVED
    )
    policy = policies.in_effect(now)
    if request.consent.access_grant_ref is None:
        return ReviewContext(approved, None, now, policy)
    try:
        grant = _lookup_grant(request, grants)
    except GrantsUnavailable as error:
        return ReviewContext(approved, None, now, policy, grant_unavailable=str(error))
    return ReviewContext(approved, grant, now, policy)


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
    policies: PolicyHistory,
    clock: Callable[[], datetime],
) -> RequestView:
    """Checked under the governance policy in effect now."""
    request = store.request(request_ref)
    if request is None:
        raise RequestNotFound(request_ref)
    now = clock()
    context = _context(request, grants, applications, policies, now)
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
    audit: AuditTrail,
    clock: Callable[[], datetime],
) -> SynchronizationRequest:
    """Record a pending request. Raises InvalidSynchronizationRequest."""
    now = clock()
    request = store.submit(
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
    record(
        audit,
        now,
        AuditAction.REQUEST_RECEIVED,
        AuditDomain.SYNCHRONIZATION,
        request.submitted_by_ref,
        SubjectType.SYNCHRONIZATION_REQUEST,
        request.request_ref,
        (request.requester_organization_ref, request.target_organization_ref),
    )
    return request


def decide_request(
    request_ref: str,
    reviewer_ref: str,
    draft: SyncDecisionDraft,
    store: SynchronizationStore,
    reviewers: ReviewerDirectory,
    grants: PatientGrantDirectory,
    applications: HospitalApplicationStore,
    policies: PolicyHistory,
    audit: AuditTrail,
    clock: Callable[[], datetime],
    ledger: AuditLedgerPort | None = None,
) -> SynchronizationDecision:
    """Decided under the governance policy in effect now, which it cites."""
    request = store.request(request_ref)
    if request is None:
        raise RequestNotFound(request_ref)
    decision, decided = decide(
        request,
        _decision_of(request, store),
        reviewers.reviewer(reviewer_ref),
        draft,
        _context(request, grants, applications, policies, clock()),
    )
    store.record(decided, decision)
    event = record(
        audit,
        decision.decided_at,
        AuditAction.DECISION_RECORDED,
        AuditDomain.SYNCHRONIZATION,
        decision.decided_by_ref,
        SubjectType.DECISION,
        decision.decision_ref,
        (
            AUTHORITY_ORGANIZATION_REF,
            request.requester_organization_ref,
            request.target_organization_ref,
        ),
        AuditOutcome(decision.outcome.value),
    )
    # HC-191: anchored in the ledger, if any; the decision stands either way.
    anchor_recorded(ledger, event)
    return decision


def check_sync_authorization(
    decision_ref: str,
    ask: ExchangeAsk,
    store: SynchronizationStore,
    grants: PatientGrantDirectory,
    audit: AuditTrail,
    clock: Callable[[], datetime],
) -> AuthorizationCheck:
    """Recorded in the audit trail before it is answered: no audit, no answer.

    An authorization relying on a patient grant is re-verified with the Hospital Node
    holding the grant (HC-136). If that node cannot answer, nothing is authorized: the
    denial is audited (`consent_unavailable`) and GrantsUnavailable is raised."""
    decision = store.decision(decision_ref)
    request = store.request(decision.request_ref) if decision else None
    found = (decision, request) if decision and request else None
    now = clock()
    result = check_authorization(decision_ref, found, ask, now)

    def audited(
        outcome: AuditOutcome, reason: str | None, targets: tuple[str, ...] = ()
    ) -> None:
        record(
            audit,
            now,
            AuditAction.AUTHORIZATION_CHECKED,
            AuditDomain.SYNCHRONIZATION,
            ask.actor_ref,
            SubjectType.DECISION,
            decision_ref,
            (
                AUTHORITY_ORGANIZATION_REF,
                ask.requester_organization_ref,
                *targets,
            ),
            outcome,
            reason,
        )

    if result.authorized and relies_on_patient_grant(request):
        try:
            grant = _lookup_grant(request, grants)
        except GrantsUnavailable:
            audited(AuditOutcome.DENIED, "consent_unavailable")
            raise
        result = reverify_consent(result, request, grant, now)
    if result.authorized:
        audited(AuditOutcome.AUTHORIZED, None, result.target_organization_refs)
    else:
        audited(AuditOutcome.DENIED, result.reason.value)
    return result
