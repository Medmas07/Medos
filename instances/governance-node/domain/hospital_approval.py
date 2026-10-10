"""The Governance / Ethics Authority's decision on a hospital application (HC-131).

Same rules as the Governance Portal's review form (HC-073), enforced here because the
Governance Node, not a company-managed portal, decides. The minimum rationale length
comes from the governance policy in effect (HC-135), which the decision cites.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from domain.hospital_application import ApplicationStatus, HospitalApplication
from domain.policy import GovernancePolicy

GOVERNANCE_REVIEWER_ROLE = "governance_reviewer"


class Outcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Reviewer:
    person_ref: str
    role: str
    organization_ref: str


@dataclass(frozen=True)
class DecisionDraft:
    outcome: Outcome
    rationale: str
    conditions: tuple[str, ...]
    # The reviewer examined every finding of the application.
    findings_acknowledged: bool


@dataclass(frozen=True)
class HospitalApprovalDecision:
    decision_ref: str
    application_ref: str
    organization_ref: str
    outcome: Outcome
    decided_by_ref: str
    decided_at: datetime
    rationale: str
    conditions: tuple[str, ...] = ()
    # The governance policy version it was decided under (HC-135).
    policy_ref: str | None = None


@dataclass(frozen=True)
class Issue:
    field: str
    message: str


class NotAwaitingReview(Exception):
    pass


class ReviewerNotAllowed(Exception):
    pass


class InvalidDecision(Exception):
    def __init__(self, issues: list[Issue]) -> None:
        super().__init__(" ".join(issue.message for issue in issues))
        self.issues = issues


def check_reviewer(application: HospitalApplication, reviewer: Reviewer | None) -> None:
    """An applicant never decides on its own application."""
    if reviewer is None:
        raise ReviewerNotAllowed("The reviewer is unknown to the Governance Node.")
    if reviewer.role != GOVERNANCE_REVIEWER_ROLE:
        raise ReviewerNotAllowed("Only a governance reviewer may decide.")
    if reviewer.organization_ref == application.organization_ref:
        raise ReviewerNotAllowed(
            "A member of the applicant organization cannot decide on its own "
            "application."
        )


def rationale_issues(rationale: str, policy: GovernancePolicy) -> list[Issue]:
    """The policy's minimum rationale length, for every kind of decision."""
    length = policy.minimum_rationale_length
    if len(rationale.strip()) < length:
        return [
            Issue("rationale", f"The rationale must have at least {length} characters.")
        ]
    return []


def review_issues(
    application: HospitalApplication, draft: DecisionDraft, policy: GovernancePolicy
) -> list[Issue]:
    issues = rationale_issues(draft.rationale, policy)
    if application.findings.count and not draft.findings_acknowledged:
        issues.append(
            Issue(
                "findings_acknowledged",
                "Every finding must be examined and acknowledged before deciding.",
            )
        )
    conditions = _clean(draft.conditions)
    if (
        draft.outcome is Outcome.APPROVED
        and application.findings.incomplete
        and not conditions
    ):
        issues.append(
            Issue(
                "conditions",
                "Approving an application with missing documents or unaccepted "
                "agreements requires at least one condition.",
            )
        )
    if draft.outcome is Outcome.REJECTED and conditions:
        issues.append(Issue("conditions", "A rejection carries no condition."))
    return issues


def decide(
    application: HospitalApplication,
    reviewer: Reviewer | None,
    draft: DecisionDraft,
    policy: GovernancePolicy,
    decided_at: datetime,
) -> tuple[HospitalApprovalDecision, HospitalApplication]:
    """The decision and the decided application, or why it cannot be recorded."""
    if not application.awaiting_review:
        raise NotAwaitingReview(
            f"Application {application.application_ref} is {application.status.value}"
            + (
                f" and already has decision {application.decision_ref}."
                if application.decision_ref
                else ", not awaiting human review."
            )
        )
    check_reviewer(application, reviewer)
    issues = review_issues(application, draft, policy)
    if issues:
        raise InvalidDecision(issues)
    if decided_at.tzinfo is None:
        raise ValueError("decided_at must carry a UTC offset")
    decision = HospitalApprovalDecision(
        decision_ref=application.decision_ref_to_record,
        application_ref=application.application_ref,
        organization_ref=application.organization_ref,
        outcome=draft.outcome,
        decided_by_ref=reviewer.person_ref,
        decided_at=decided_at,
        rationale=draft.rationale.strip(),
        conditions=_clean(draft.conditions),
        policy_ref=policy.policy_ref,
    )
    decided = replace(
        application,
        status=ApplicationStatus(draft.outcome.value),
        decision_ref=decision.decision_ref,
    )
    return decision, decided


def _clean(conditions: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(c.strip() for c in conditions if c.strip())
