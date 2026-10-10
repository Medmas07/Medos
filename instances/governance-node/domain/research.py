"""Research access requests and their Compute-to-Data authorizations (HC-133).

Same review rules as the Governance Portal's research form (HC-078), enforced here
because the Governance Node, not a company-managed portal, decides. An approval only
narrows the request, and the Research Service checks it before each job
(contracts/api/research/research-authorization-check.v1.yaml).
"""

import calendar
import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import Enum

from domain.hospital_approval import (
    GOVERNANCE_REVIEWER_ROLE,
    MIN_RATIONALE_LENGTH,
    InvalidDecision,
    Issue,
    Outcome,
    Reviewer,
    ReviewerNotAllowed,
)

# D2 demo policy, as in dec-rar-001.
MAX_VALIDITY_MONTHS = 12
MINIMUM_CELL_SIZE_FLOOR = 10
AUTHORITY_ORGANIZATION_REF = "org-governance"

_OPAQUE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_REQUEST_REF = re.compile(r"rar-[A-Za-z0-9._:-]{1,123}")
# Variable names of research-authorization-check.v1.yaml.
_VARIABLE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,99}")


class InvalidResearchRequest(ValueError):
    pass


class NotUnderReview(Exception):
    pass


class RequestStatus(str, Enum):
    UNDER_REVIEW = "under_review"
    AUTHORIZED = "authorized"  # approved, validity not ended
    EXPIRED = "expired"  # approved, validity ended: authorizes nothing
    REJECTED = "rejected"


class CheckState(str, Enum):
    PASS = "pass"
    FAIL = "fail"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidResearchRequest(message)


@dataclass(frozen=True)
class Population:
    """Bounds of the population; None means unbounded on that side."""

    age_min: int | None = None
    age_max: int | None = None
    encounter_from: date | None = None
    encounter_to: date | None = None

    def __post_init__(self) -> None:
        _require(
            any(
                v is not None
                for v in (
                    self.age_min,
                    self.age_max,
                    self.encounter_from,
                    self.encounter_to,
                )
            ),
            "data_scope.population needs at least one bound",
        )
        for age in (self.age_min, self.age_max):
            _require(age is None or 0 <= age <= 130, "ages must be between 0 and 130")
        _require(
            self.age_min is None
            or self.age_max is None
            or self.age_min <= self.age_max,
            "data_scope.population.age_min must not exceed age_max",
        )
        _require(
            self.encounter_from is None
            or self.encounter_to is None
            or self.encounter_from <= self.encounter_to,
            "data_scope.population.encounter_from must not be after encounter_to",
        )

    def contains(self, other: "Population") -> bool:
        """Every bound of `other` lies inside this population's bounds."""

        def lower_ok(mine, theirs) -> bool:
            return mine is None or (theirs is not None and theirs >= mine)

        def upper_ok(mine, theirs) -> bool:
            return mine is None or (theirs is not None and theirs <= mine)

        return (
            lower_ok(self.age_min, other.age_min)
            and upper_ok(self.age_max, other.age_max)
            and lower_ok(self.encounter_from, other.encounter_from)
            and upper_ok(self.encounter_to, other.encounter_to)
        )


@dataclass(frozen=True)
class DataScope:
    population: Population
    # In the order requested.
    variables: tuple[str, ...]

    def __post_init__(self) -> None:
        _require(bool(self.variables), "data_scope.variables must not be empty")
        _require(
            len(set(self.variables)) == len(self.variables),
            "data_scope.variables must be unique",
        )
        for variable in self.variables:
            _require(
                bool(_VARIABLE.fullmatch(variable)),
                f"data_scope.variables: {variable!r} is not a variable name",
            )


@dataclass(frozen=True)
class ResearchRequest:
    request_ref: str
    project_ref: str
    project_title: str
    research_organization_ref: str
    principal_investigator_ref: str
    submitted_by_ref: str
    purpose: str
    # In the order requested.
    participating_organization_refs: tuple[str, ...]
    data_scope: DataScope
    protocol_document_ref: str | None
    submitted_at: datetime
    decision_ref: str | None = None

    def __post_init__(self) -> None:
        _require(
            bool(_REQUEST_REF.fullmatch(self.request_ref)),
            "request_ref must be 'rar-' and an opaque suffix",
        )
        refs = [
            ("project_ref", self.project_ref),
            ("research_organization_ref", self.research_organization_ref),
            ("principal_investigator_ref", self.principal_investigator_ref),
            ("submitted_by_ref", self.submitted_by_ref),
            *(
                ("participating_organization_refs", r)
                for r in self.participating_organization_refs
            ),
        ]
        if self.protocol_document_ref is not None:
            refs.append(("protocol_document_ref", self.protocol_document_ref))
        for field, value in refs:
            _require(
                bool(_OPAQUE_REF.fullmatch(value)),
                f"{field} must hold opaque references",
            )
        _require(
            0 < len(self.project_title.strip()) <= 200,
            "project_title must be 1-200 characters",
        )
        _require(
            0 < len(self.purpose.strip()) <= 500, "purpose must be 1-500 characters"
        )
        participants = self.participating_organization_refs
        _require(
            bool(participants), "participating_organization_refs must not be empty"
        )
        _require(
            len(set(participants)) == len(participants),
            "participating_organization_refs must be unique",
        )
        _require(
            self.submitted_at.tzinfo is not None, "submitted_at needs a UTC offset"
        )

    @property
    def decision_ref_to_record(self) -> str:
        """The reference its decision gets: one decision per request."""
        return "dec-" + self.request_ref


@dataclass(frozen=True)
class ResearchDecision:
    decision_ref: str
    request_ref: str
    outcome: Outcome
    decided_by_ref: str
    decided_at: datetime
    rationale: str
    conditions: tuple[str, ...] = ()
    # Set for an approval only: what it authorizes.
    approved_organization_refs: tuple[str, ...] = ()
    approved_variables: tuple[str, ...] = ()
    minimum_cell_size: int | None = None
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        approved = self.outcome is Outcome.APPROVED
        authorizes = bool(
            self.approved_organization_refs
            and self.approved_variables
            and self.minimum_cell_size is not None
            and self.valid_until is not None
        )
        empty = not (
            self.approved_organization_refs
            or self.approved_variables
            or self.minimum_cell_size is not None
            or self.valid_until is not None
        )
        if (approved and not authorizes) or (not approved and not empty):
            raise ValueError(
                "an approval, and only an approval, says what it authorizes"
            )


@dataclass(frozen=True)
class Check:
    check: str  # protocol, organizations
    state: CheckState
    detail: str


@dataclass(frozen=True)
class ResearchDecisionDraft:
    outcome: Outcome
    rationale: str
    conditions: tuple[str, ...]
    approved_organization_refs: tuple[str, ...] | None
    approved_variables: tuple[str, ...] | None
    validity_months: int | None
    minimum_cell_size: int | None


def add_months(start: datetime, months: int) -> datetime:
    """The same time `months` calendar months later, on the last day if shorter."""
    index = start.month - 1 + months
    year, month = start.year + index // 12, index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def status_at(decision: ResearchDecision | None, now: datetime) -> RequestStatus:
    if decision is None:
        return RequestStatus.UNDER_REVIEW
    if decision.outcome is Outcome.REJECTED:
        return RequestStatus.REJECTED
    return (
        RequestStatus.AUTHORIZED
        if now < decision.valid_until
        else RequestStatus.EXPIRED
    )


def eligible_organizations(
    request: ResearchRequest, approved_organizations: frozenset[str]
) -> tuple[str, ...]:
    """Participating organizations an approval may name: approved by the Authority."""
    return tuple(
        r
        for r in request.participating_organization_refs
        if r in approved_organizations
    )


def checks(
    request: ResearchRequest, approved_organizations: frozenset[str]
) -> list[Check]:
    protocol = Check(
        "protocol",
        CheckState.PASS if request.protocol_document_ref else CheckState.FAIL,
        f"Protocol {request.protocol_document_ref} is provided."
        if request.protocol_document_ref
        else "No research protocol is provided.",
    )
    eligible = eligible_organizations(request, approved_organizations)
    excluded = [r for r in request.participating_organization_refs if r not in eligible]
    if not eligible:
        detail = "No participating organization is approved by the Authority."
    elif excluded:
        detail = (
            f"{', '.join(eligible)} approved by the Authority; "
            f"{', '.join(excluded)} excluded, not approved."
        )
    else:
        detail = f"{', '.join(eligible)} approved by the Authority."
    organizations = Check(
        "organizations", CheckState.PASS if eligible else CheckState.FAIL, detail
    )
    return [protocol, organizations]


def _check_reviewer(request: ResearchRequest, reviewer: Reviewer | None) -> None:
    if reviewer is None:
        raise ReviewerNotAllowed("The reviewer is unknown to the Governance Node.")
    if reviewer.role != GOVERNANCE_REVIEWER_ROLE:
        raise ReviewerNotAllowed("Only a governance reviewer may decide.")
    if (
        reviewer.person_ref
        in (request.submitted_by_ref, request.principal_investigator_ref)
        or reviewer.organization_ref == request.research_organization_ref
        or reviewer.organization_ref in request.participating_organization_refs
    ):
        raise ReviewerNotAllowed(
            "A member of the research team or of a participating organization cannot "
            "decide on this request."
        )


def review_issues(
    request: ResearchRequest,
    draft: ResearchDecisionDraft,
    approved_organizations: frozenset[str],
) -> list[Issue]:
    issues = []
    if len(draft.rationale.strip()) < MIN_RATIONALE_LENGTH:
        issues.append(
            Issue(
                "rationale",
                f"The rationale must have at least {MIN_RATIONALE_LENGTH} characters.",
            )
        )
    if draft.outcome is Outcome.REJECTED:
        if _clean(draft.conditions):
            issues.append(Issue("conditions", "A rejection carries no condition."))
        for field in (
            "approved_organization_refs",
            "approved_variables",
            "validity_months",
            "minimum_cell_size",
        ):
            if getattr(draft, field) is not None:
                issues.append(Issue(field, "A rejection authorizes nothing."))
        return issues
    failed = [
        c.check
        for c in checks(request, approved_organizations)
        if c.state is CheckState.FAIL
    ]
    if failed:
        issues.append(
            Issue(
                "checks",
                f"Approval is impossible while these checks fail: {', '.join(failed)}. "
                "Only a rejection is possible.",
            )
        )
    eligible = eligible_organizations(request, approved_organizations)
    if not _subset(draft.approved_organization_refs, eligible):
        issues.append(
            Issue(
                "approved_organization_refs",
                "Approve at least one eligible participating organization, and only those.",
            )
        )
    if not _subset(draft.approved_variables, request.data_scope.variables):
        issues.append(
            Issue(
                "approved_variables",
                "Approve at least one of the requested variables, and only those.",
            )
        )
    months = draft.validity_months
    if months is None or not 1 <= months <= MAX_VALIDITY_MONTHS:
        issues.append(
            Issue(
                "validity_months",
                f"The validity must be between 1 and {MAX_VALIDITY_MONTHS} months.",
            )
        )
    cell = draft.minimum_cell_size
    if cell is None or cell < MINIMUM_CELL_SIZE_FLOOR:
        issues.append(
            Issue(
                "minimum_cell_size",
                f"The minimum cell size must be at least {MINIMUM_CELL_SIZE_FLOOR}.",
            )
        )
    return issues


def decide(
    request: ResearchRequest,
    decision_so_far: ResearchDecision | None,
    reviewer: Reviewer | None,
    draft: ResearchDecisionDraft,
    approved_organizations: frozenset[str],
    now: datetime,
) -> tuple[ResearchDecision, ResearchRequest]:
    """The decision and the decided request, or why it cannot be recorded."""
    if decision_so_far is not None or request.decision_ref is not None:
        state = decision_so_far.outcome.value if decision_so_far else "decided"
        raise NotUnderReview(
            f"Request {request.request_ref} is {state} and already has decision "
            f"{request.decision_ref}."
        )
    _check_reviewer(request, reviewer)
    issues = review_issues(request, draft, approved_organizations)
    if issues:
        raise InvalidDecision(issues)
    if now.tzinfo is None:
        raise ValueError("now must carry a UTC offset")
    approved = draft.outcome is Outcome.APPROVED
    decision = ResearchDecision(
        decision_ref=request.decision_ref_to_record,
        request_ref=request.request_ref,
        outcome=draft.outcome,
        decided_by_ref=reviewer.person_ref,
        decided_at=now,
        rationale=draft.rationale.strip(),
        conditions=_clean(draft.conditions),
        # In the request's order, so the decision reads like the request.
        approved_organization_refs=tuple(
            r
            for r in request.participating_organization_refs
            if approved and r in draft.approved_organization_refs
        ),
        approved_variables=tuple(
            v
            for v in request.data_scope.variables
            if approved and v in draft.approved_variables
        ),
        minimum_cell_size=draft.minimum_cell_size if approved else None,
        valid_until=add_months(now, draft.validity_months) if approved else None,
    )
    return decision, replace(request, decision_ref=decision.decision_ref)


class DenialReason(str, Enum):
    """The order is the order of the checks: the first failing one is reported."""

    NOT_APPROVED = "not_approved"
    NOT_YET_VALID = "not_yet_valid"
    EXPIRED = "expired"
    PROJECT_MISMATCH = "project_mismatch"
    REQUESTER_MISMATCH = "requester_mismatch"
    ORGANIZATION_NOT_APPROVED = "organization_not_approved"
    VARIABLE_NOT_APPROVED = "variable_not_approved"
    POPULATION_EXCEEDED = "population_exceeded"


@dataclass(frozen=True)
class JobAsk:
    """What the Research Service wants to run under a decision."""

    project_ref: str
    requested_by: str
    purpose: str
    target_organization_refs: frozenset[str]
    population: Population
    variables: frozenset[str]


@dataclass(frozen=True)
class AuthorizationAnswer:
    decision: ResearchDecision
    reason: DenialReason | None  # None: approved

    @property
    def approved(self) -> bool:
        return self.reason is None


def check_authorization(
    decision: ResearchDecision, request: ResearchRequest, ask: JobAsk, now: datetime
) -> AuthorizationAnswer:
    """Does this decision authorize this job now? Deny by default."""

    def answer(reason: DenialReason | None) -> AuthorizationAnswer:
        return AuthorizationAnswer(decision, reason)

    if decision.outcome is not Outcome.APPROVED:
        return answer(DenialReason.NOT_APPROVED)
    if now < decision.decided_at:
        return answer(DenialReason.NOT_YET_VALID)
    if now >= decision.valid_until:
        return answer(DenialReason.EXPIRED)
    if ask.project_ref != request.project_ref:
        return answer(DenialReason.PROJECT_MISMATCH)
    if ask.requested_by not in (
        request.principal_investigator_ref,
        request.submitted_by_ref,
    ):
        return answer(DenialReason.REQUESTER_MISMATCH)
    if not ask.target_organization_refs <= set(decision.approved_organization_refs):
        return answer(DenialReason.ORGANIZATION_NOT_APPROVED)
    if not ask.variables <= set(decision.approved_variables):
        return answer(DenialReason.VARIABLE_NOT_APPROVED)
    if not request.data_scope.population.contains(ask.population):
        return answer(DenialReason.POPULATION_EXCEEDED)
    return answer(None)


def _subset(chosen: tuple[str, ...] | None, allowed: tuple[str, ...]) -> bool:
    return bool(chosen) and set(chosen) <= set(allowed)


def _clean(conditions: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(c.strip() for c in conditions if c.strip())
