"""The governance audit trail (HC-134): what the Governance / Ethics Authority did.

An event is minimized: who acted, on what subject, with which outcome, and which
organizations are concerned. It never carries a patient reference, a purpose, a
rationale, a data scope, or any clinical content; the subject's reference leads to
those, through the API that owns them. Events are append-only.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

_EVENT_REF = re.compile(r"^evt-[A-Za-z0-9._:-]{1,124}$")
_REASON = re.compile(r"^[a-z][a-z_]{0,63}$")


class InvalidAuditEvent(ValueError):
    pass


class AuditAction(str, Enum):
    APPLICATION_SUBMITTED = "application_submitted"
    REQUEST_RECEIVED = "request_received"
    DECISION_RECORDED = "decision_recorded"
    AUTHORIZATION_CHECKED = "authorization_checked"
    # HC-215: the security of the Node itself.
    SIGNED_IN = "signed_in"
    SIGN_IN_REFUSED = "sign_in_refused"
    ACCESS_DENIED = "access_denied"


class AuditDomain(str, Enum):
    HOSPITAL_APPROVAL = "hospital_approval"
    SYNCHRONIZATION = "synchronization"
    RESEARCH = "research"
    SECURITY = "security"


class SubjectType(str, Enum):
    HOSPITAL_APPLICATION = "hospital_application"
    SYNCHRONIZATION_REQUEST = "synchronization_request"
    RESEARCH_ACCESS_REQUEST = "research_access_request"
    DECISION = "decision"
    # The account signing in.
    PERSON = "person"
    # The permission a protected route needs (domain/access_control.py).
    PERMISSION = "permission"


class AuditOutcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTHORIZED = "authorized"
    DENIED = "denied"


# The subject and the outcomes each action allows; None: no outcome.
_RULES: dict[AuditAction, tuple[frozenset[SubjectType], frozenset]] = {
    AuditAction.APPLICATION_SUBMITTED: (
        frozenset({SubjectType.HOSPITAL_APPLICATION}),
        frozenset({None}),
    ),
    AuditAction.REQUEST_RECEIVED: (
        frozenset(
            {SubjectType.SYNCHRONIZATION_REQUEST, SubjectType.RESEARCH_ACCESS_REQUEST}
        ),
        frozenset({None}),
    ),
    AuditAction.DECISION_RECORDED: (
        frozenset({SubjectType.DECISION}),
        frozenset({AuditOutcome.APPROVED, AuditOutcome.REJECTED}),
    ),
    AuditAction.AUTHORIZATION_CHECKED: (
        frozenset({SubjectType.DECISION}),
        frozenset({AuditOutcome.AUTHORIZED, AuditOutcome.DENIED}),
    ),
    AuditAction.SIGNED_IN: (frozenset({SubjectType.PERSON}), frozenset({None})),
    AuditAction.SIGN_IN_REFUSED: (
        frozenset({SubjectType.PERSON}),
        frozenset({AuditOutcome.DENIED}),
    ),
    AuditAction.ACCESS_DENIED: (
        frozenset({SubjectType.PERMISSION}),
        frozenset({AuditOutcome.DENIED}),
    ),
}
_SECURITY_ACTIONS = frozenset(
    {AuditAction.SIGNED_IN, AuditAction.SIGN_IN_REFUSED, AuditAction.ACCESS_DENIED}
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidAuditEvent(message)


@dataclass(frozen=True)
class AuditEvent:
    event_ref: str
    recorded_at: datetime
    action: AuditAction
    domain: AuditDomain
    # None when no person is known, as for a seed request received.
    actor_ref: str | None
    subject_type: SubjectType
    subject_ref: str
    outcome: AuditOutcome | None
    # The first failing reason of a denied authorization check, sign-in, or access.
    reason: str | None
    # The organizations concerned, the Authority first when it acted.
    organization_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require(
            bool(_EVENT_REF.fullmatch(self.event_ref)),
            "event_ref must be 'evt-' and an opaque suffix",
        )
        _require(self.recorded_at.tzinfo is not None, "recorded_at needs a UTC offset")
        for field, value in (
            ("actor_ref", self.actor_ref),
            ("subject_ref", self.subject_ref),
            *(("organization_refs", r) for r in self.organization_refs),
        ):
            # Callers' references are kept as given: the Research Service's check
            # allows any 1-100 characters.
            _require(
                value is None or (0 < len(value) <= 128 and value.isprintable()),
                f"{field} must hold references of 1-128 printable characters",
            )
        _require(bool(self.organization_refs), "organization_refs must not be empty")
        _require(
            len(set(self.organization_refs)) == len(self.organization_refs),
            "organization_refs must be unique",
        )
        subjects, outcomes = _RULES[self.action]
        _require(
            self.subject_type in subjects,
            f"{self.action.value} cannot concern a {self.subject_type.value}",
        )
        _require(
            self.outcome in outcomes,
            f"{self.action.value} cannot have outcome {self.outcome}",
        )
        _require(
            (self.action in _SECURITY_ACTIONS) == (self.domain is AuditDomain.SECURITY),
            "security actions, and only they, belong to the security domain",
        )
        denied = self.outcome is AuditOutcome.DENIED
        _require(
            (self.reason is not None) == denied,
            "a reason is given for a denial, and only then",
        )
        _require(
            self.reason is None or bool(_REASON.fullmatch(self.reason)),
            "reason must be a reason code",
        )


@dataclass(frozen=True)
class AuditFilter:
    domain: AuditDomain | None = None
    action: AuditAction | None = None
    organization_ref: str | None = None
    subject_ref: str | None = None

    def matches(self, event: AuditEvent) -> bool:
        return (
            self.domain in (None, event.domain)
            and self.action in (None, event.action)
            and self.subject_ref in (None, event.subject_ref)
            and (
                self.organization_ref is None
                or self.organization_ref in event.organization_refs
            )
        )
