"""Inter-hospital synchronization requests and their temporary authorizations (HC-132).

Same review rules as the Governance Portal's synchronization form (HC-076), enforced
here because the Governance Node, not a company-managed portal, decides. An approval is
a temporary authorization that the Federation Service checks before each exchange
(contracts/federation/sync-authorization-check.v1.yaml). The consent bases accepted, how
each is checked, the longest authorization, and the minimum rationale length come from
the governance policy in effect (HC-135), which the decision cites. A patient grant is
evaluated against the grants the target organization's Hospital Node holds, when
reviewing and again before each exchange (HC-136): a grant withdrawn there stops the
authorization.
"""

import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum

from domain.hospital_approval import (
    InvalidDecision,
    Issue,
    Outcome,
    Reviewer,
    ReviewerNotAllowed,
    rationale_issues,
)
from domain.policy import MAX_SYNC_DURATION_DAYS, ConsentMode, GovernancePolicy

# The contract's limit on a requested duration; the policy may approve less.
MAX_DURATION_DAYS = MAX_SYNC_DURATION_DAYS

_OPAQUE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_REQUEST_REF = re.compile(r"sync-[A-Za-z0-9._:-]{1,123}")


class InvalidSynchronizationRequest(ValueError):
    pass


class NotPending(Exception):
    pass


class ScopeItem(str, Enum):
    ENCOUNTERS = "encounters"
    MEDICATIONS = "medications"
    LAB_REPORTS = "lab_reports"


class ConsentBasis(str, Enum):
    PATIENT_GRANT = "patient_grant"
    # Not verifiable by the Governance Node: the reviewer must confirm them.
    SIGNED_CONSENT_FORM = "signed_consent_form"
    EMERGENCY_OVERRIDE = "emergency_override"
    NONE = "none"


class RequestStatus(str, Enum):
    """What a request means when answering."""

    PENDING = "pending"
    ACTIVE = "active"  # approved, authorization not ended
    EXPIRED = "expired"  # approved, authorization ended: authorizes nothing
    REJECTED = "rejected"


class CheckState(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    MANUAL = "manual"  # the Node cannot verify it; the reviewer confirms it


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidSynchronizationRequest(message)


@dataclass(frozen=True)
class Consent:
    basis: ConsentBasis
    access_grant_ref: str | None = None

    def __post_init__(self) -> None:
        names_grant = self.access_grant_ref is not None
        _require(
            names_grant == (self.basis is ConsentBasis.PATIENT_GRANT),
            "consent.access_grant_ref is required for a patient_grant basis, "
            "and only then",
        )
        _require(
            not names_grant or bool(_OPAQUE_REF.fullmatch(self.access_grant_ref)),
            "consent.access_grant_ref must be an opaque reference",
        )


@dataclass(frozen=True)
class SynchronizationRequest:
    request_ref: str
    requester_organization_ref: str
    target_organization_ref: str
    # Pseudonymous patient reference, never a name.
    patient_ref: str
    purpose: str
    scope: frozenset[ScopeItem]
    duration_days: int
    consent: Consent
    submitted_at: datetime
    submitted_by_ref: str | None = None
    decision_ref: str | None = None

    def __post_init__(self) -> None:
        _require(
            bool(_REQUEST_REF.fullmatch(self.request_ref)),
            "request_ref must be 'sync-' and an opaque suffix",
        )
        for field in (
            "requester_organization_ref",
            "target_organization_ref",
            "patient_ref",
        ):
            _require(
                bool(_OPAQUE_REF.fullmatch(getattr(self, field))),
                f"{field} must be an opaque reference",
            )
        _require(
            self.requester_organization_ref != self.target_organization_ref,
            "target_organization_ref must differ from requester_organization_ref",
        )
        _require(
            0 < len(self.purpose.strip()) <= 200, "purpose must be 1-200 characters"
        )
        _require(bool(self.scope), "scope must not be empty")
        _require(
            1 <= self.duration_days <= MAX_DURATION_DAYS,
            f"duration_days must be between 1 and {MAX_DURATION_DAYS}",
        )
        _require(
            self.submitted_at.tzinfo is not None, "submitted_at needs a UTC offset"
        )

    @property
    def decision_ref_to_record(self) -> str:
        """The reference its decision gets: one decision per request."""
        return "dec-" + self.request_ref


@dataclass(frozen=True)
class PatientGrant:
    """A patient's access grant, as the Governance Node knows it (MOCKED source)."""

    grant_ref: str
    patient_ref: str
    scope: frozenset[ScopeItem]
    expires_at: datetime
    revoked: bool = False

    def active_at(self, now: datetime) -> bool:
        return not self.revoked and now < self.expires_at


@dataclass(frozen=True)
class SynchronizationDecision:
    decision_ref: str
    request_ref: str
    outcome: Outcome
    decided_by_ref: str
    decided_at: datetime
    rationale: str
    conditions: tuple[str, ...] = ()
    # Set for an approval only: the temporary authorization.
    approved_days: int | None = None
    valid_until: datetime | None = None
    # The governance policy version it was decided under (HC-135).
    policy_ref: str | None = None

    def __post_init__(self) -> None:
        approved = self.outcome is Outcome.APPROVED
        if approved != (
            self.approved_days is not None and self.valid_until is not None
        ):
            raise ValueError("an approval, and only an approval, has a duration")


@dataclass(frozen=True)
class Check:
    check: str  # organizations, consent, duration
    state: CheckState
    detail: str


@dataclass(frozen=True)
class SyncDecisionDraft:
    outcome: Outcome
    rationale: str
    conditions: tuple[str, ...]
    approved_days: int | None
    # The reviewer verified, outside the Node, the checks in state MANUAL.
    manual_checks_confirmed: bool


@dataclass(frozen=True)
class ReviewContext:
    """What the checks need, evaluated at `now`."""

    approved_organizations: frozenset[str]
    # The grant named by the consent; None if it names none or an unknown one.
    grant: PatientGrant | None
    now: datetime
    # The governance policy in effect at `now`.
    policy: GovernancePolicy
    # Why the grant could not be looked up, when its holder could not answer.
    grant_unavailable: str | None = None


def status_at(
    request: SynchronizationRequest,
    decision: SynchronizationDecision | None,
    now: datetime,
) -> RequestStatus:
    if decision is None:
        return RequestStatus.PENDING
    if decision.outcome is Outcome.REJECTED:
        return RequestStatus.REJECTED
    return RequestStatus.ACTIVE if now < decision.valid_until else RequestStatus.EXPIRED


def _grant_days_left(
    request: SynchronizationRequest, context: ReviewContext
) -> int | None:
    if request.consent.basis is not ConsentBasis.PATIENT_GRANT or context.grant is None:
        return None
    seconds_left = (context.grant.expires_at - context.now).total_seconds()
    return max(0, math.floor(seconds_left / timedelta(days=1).total_seconds()))


def max_approved_days(request: SynchronizationRequest, context: ReviewContext) -> int:
    """The requested duration, never beyond the policy's longest authorization or the
    patient grant. 0: none possible."""
    limits = [request.duration_days, context.policy.maximum_sync_duration_days]
    grant_days = _grant_days_left(request, context)
    if grant_days is not None:
        limits.append(grant_days)
    return min(limits)


def grant_problem(
    request: SynchronizationRequest, grant: PatientGrant | None, now: datetime
) -> str | None:
    """Why the patient grant does not support this request now; None if it does."""
    ref = request.consent.access_grant_ref
    if grant is None:
        return (
            f"Grant {ref} is unknown to the Hospital Node of "
            f"{request.target_organization_ref}."
        )
    if grant.revoked:
        return f"Grant {ref} was revoked."
    if not grant.active_at(now):
        return f"Grant {ref} expired on {grant.expires_at.isoformat()}."
    if grant.patient_ref != request.patient_ref:
        return f"Grant {ref} concerns another patient."
    uncovered = sorted(item.value for item in request.scope - grant.scope)
    if uncovered:
        return f"Grant {ref} does not cover: {', '.join(uncovered)}."
    return None


def checks(request: SynchronizationRequest, context: ReviewContext) -> list[Check]:
    requester = request.requester_organization_ref
    target = request.target_organization_ref
    approved = {requester, target} <= context.approved_organizations
    organizations = Check(
        "organizations",
        CheckState.PASS if approved else CheckState.FAIL,
        f"{requester} and {target} are distinct organizations approved by the "
        "Authority."
        if approved
        else "The requester and the target must be two distinct organizations "
        "approved by the Authority.",
    )

    basis = request.consent.basis
    policy = context.policy
    mode = policy.consent_mode(basis.value)
    if basis is ConsentBasis.NONE:
        consent = Check(
            "consent", CheckState.FAIL, "No patient grant or legal basis is given."
        )
    elif mode is None:
        consent = Check(
            "consent",
            CheckState.FAIL,
            f"Governance policy v{policy.version} does not accept {basis.value} as a "
            "consent basis.",
        )
    elif mode is ConsentMode.VERIFIED and context.grant_unavailable:
        consent = Check(
            "consent",
            CheckState.FAIL,
            f"Grant {request.consent.access_grant_ref} could not be verified: "
            f"{context.grant_unavailable}",
        )
    elif mode is ConsentMode.VERIFIED:
        problem = grant_problem(request, context.grant, context.now)
        consent = Check(
            "consent",
            CheckState.FAIL if problem else CheckState.PASS,
            problem
            or f"{request.consent.access_grant_ref} is active until "
            f"{context.grant.expires_at.isoformat()} and covers the requested scope.",
        )
    else:
        what = (
            "A signed consent form"
            if basis is ConsentBasis.SIGNED_CONSENT_FORM
            else "An emergency override"
        )
        consent = Check(
            "consent",
            CheckState.MANUAL,
            f"{what} cannot be verified by the Governance Node; the reviewer must "
            "confirm it.",
        )

    most = max_approved_days(request, context)
    asked = request.duration_days
    grant_days = _grant_days_left(request, context)
    if most >= asked:
        detail = f"{asked} days requested."
    elif most < 1:
        detail = "No duration is possible before the patient grant ends."
    elif grant_days is not None and grant_days == most:
        detail = (
            f"{asked} days requested, limited to {most} days by the end of the "
            "patient grant."
        )
    else:
        detail = (
            f"{asked} days requested, limited to {most} days by governance policy "
            f"v{policy.version}."
        )
    duration = Check(
        "duration", CheckState.PASS if most >= 1 else CheckState.FAIL, detail
    )
    return [organizations, consent, duration]


def _check_reviewer(request: SynchronizationRequest, reviewer: Reviewer | None) -> None:
    if reviewer is None:
        raise ReviewerNotAllowed("The reviewer is unknown to the Governance Node.")
    if not reviewer.may_review:
        raise ReviewerNotAllowed("Only a governance reviewer may decide.")
    if reviewer.organization_ref in (
        request.requester_organization_ref,
        request.target_organization_ref,
    ):
        raise ReviewerNotAllowed(
            "A member of the requesting or target organization cannot decide on "
            "this request."
        )


def review_issues(
    request: SynchronizationRequest, draft: SyncDecisionDraft, context: ReviewContext
) -> list[Issue]:
    issues = rationale_issues(draft.rationale, context.policy)
    if draft.outcome is Outcome.REJECTED:
        if _clean(draft.conditions):
            issues.append(Issue("conditions", "A rejection carries no condition."))
        if draft.approved_days is not None:
            issues.append(
                Issue("approved_days", "A rejection has no approved duration.")
            )
        return issues
    results = checks(request, context)
    failed = [c.check for c in results if c.state is CheckState.FAIL]
    if failed:
        issues.append(
            Issue(
                "checks",
                f"Approval is impossible while these checks fail: {', '.join(failed)}. "
                "Only a rejection is possible.",
            )
        )
    if (
        any(c.state is CheckState.MANUAL for c in results)
        and not draft.manual_checks_confirmed
    ):
        issues.append(
            Issue(
                "manual_checks_confirmed",
                "Confirm that the consent basis was verified outside the Governance "
                "Node.",
            )
        )
    most = max_approved_days(request, context)
    if not failed and not (
        draft.approved_days is not None and 1 <= draft.approved_days <= most
    ):
        issues.append(
            Issue(
                "approved_days",
                f"The approved duration must be between 1 and {most} days.",
            )
        )
    return issues


def decide(
    request: SynchronizationRequest,
    decision_so_far: SynchronizationDecision | None,
    reviewer: Reviewer | None,
    draft: SyncDecisionDraft,
    context: ReviewContext,
) -> tuple[SynchronizationDecision, SynchronizationRequest]:
    """The decision and the decided request, or why it cannot be recorded."""
    if decision_so_far is not None or request.decision_ref is not None:
        state = decision_so_far.outcome.value if decision_so_far else "decided"
        raise NotPending(
            f"Request {request.request_ref} is {state} and already has decision "
            f"{request.decision_ref}."
        )
    _check_reviewer(request, reviewer)
    issues = review_issues(request, draft, context)
    if issues:
        raise InvalidDecision(issues)
    now = context.now
    if now.tzinfo is None:
        raise ValueError("now must carry a UTC offset")
    approved = draft.outcome is Outcome.APPROVED
    decision = SynchronizationDecision(
        decision_ref=request.decision_ref_to_record,
        request_ref=request.request_ref,
        outcome=draft.outcome,
        decided_by_ref=reviewer.person_ref,
        decided_at=now,
        rationale=draft.rationale.strip(),
        conditions=_clean(draft.conditions),
        approved_days=draft.approved_days if approved else None,
        valid_until=now + timedelta(days=draft.approved_days) if approved else None,
        policy_ref=context.policy.policy_ref,
    )
    return decision, replace(request, decision_ref=decision.decision_ref)


class DenialReason(str, Enum):
    """The order is the order of the checks: the first failing one is reported."""

    NOT_FOUND = "not_found"
    NOT_APPROVED = "not_approved"
    NOT_YET_VALID = "not_yet_valid"
    EXPIRED = "expired"
    REQUESTER_MISMATCH = "requester_mismatch"
    PATIENT_MISMATCH = "patient_mismatch"
    SCOPE_EXCEEDED = "scope_exceeded"
    PURPOSE_MISMATCH = "purpose_mismatch"
    # Last, once everything else holds: the patient grant the approval relies on is no
    # longer active at the target organization's Hospital Node (HC-136).
    REVOKED = "revoked"


@dataclass(frozen=True)
class ExchangeAsk:
    """What the Federation Service wants to do under a decision."""

    requester_organization_ref: str
    actor_ref: str
    patient_ref: str
    scope: frozenset[ScopeItem]
    purpose: str


@dataclass(frozen=True)
class AuthorizationCheck:
    decision_ref: str
    reason: DenialReason | None  # None: authorized
    checked_at: datetime
    # Set when authorized.
    target_organization_refs: tuple[str, ...] = ()
    scope: frozenset[ScopeItem] = frozenset()
    purpose: str | None = None
    # The decision's end of validity, when it has one, even if denied.
    valid_until: datetime | None = None

    @property
    def authorized(self) -> bool:
        return self.reason is None


def check_authorization(
    decision_ref: str,
    found: tuple[SynchronizationDecision, SynchronizationRequest] | None,
    ask: ExchangeAsk,
    now: datetime,
) -> AuthorizationCheck:
    """Does this decision authorize this exchange now? Deny by default."""
    if found is None:
        return AuthorizationCheck(decision_ref, DenialReason.NOT_FOUND, now)
    decision, request = found

    def denied(reason: DenialReason) -> AuthorizationCheck:
        return AuthorizationCheck(
            decision_ref, reason, now, valid_until=decision.valid_until
        )

    if decision.outcome is not Outcome.APPROVED:
        return denied(DenialReason.NOT_APPROVED)
    if now < decision.decided_at:
        return denied(DenialReason.NOT_YET_VALID)
    if now >= decision.valid_until:
        return denied(DenialReason.EXPIRED)
    if ask.requester_organization_ref != request.requester_organization_ref:
        return denied(DenialReason.REQUESTER_MISMATCH)
    if ask.patient_ref != request.patient_ref:
        return denied(DenialReason.PATIENT_MISMATCH)
    if not ask.scope <= request.scope:
        return denied(DenialReason.SCOPE_EXCEEDED)
    if ask.purpose != request.purpose:
        return denied(DenialReason.PURPOSE_MISMATCH)
    return AuthorizationCheck(
        decision_ref,
        None,
        now,
        target_organization_refs=(request.target_organization_ref,),
        scope=request.scope,
        purpose=request.purpose,
        valid_until=decision.valid_until,
    )


def relies_on_patient_grant(request: SynchronizationRequest) -> bool:
    return request.consent.basis is ConsentBasis.PATIENT_GRANT


def reverify_consent(
    result: AuthorizationCheck,
    request: SynchronizationRequest,
    grant: PatientGrant | None,
    now: datetime,
) -> AuthorizationCheck:
    """An authorization stands only while its patient grant still supports it at the
    Hospital Node that holds it: revoked, expired, or unknown there denies it."""
    if not result.authorized or not relies_on_patient_grant(request):
        return result
    if grant_problem(request, grant, now) is None:
        return result
    return AuthorizationCheck(
        result.decision_ref,
        DenialReason.REVOKED,
        result.checked_at,
        valid_until=result.valid_until,
    )


def _clean(conditions: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(c.strip() for c in conditions if c.strip())
