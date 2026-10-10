"""The Governance / Ethics Authority's policy and the engine that applies it (HC-135).

A policy is data, not code: the Authority's rules for every decision, each version
effective from a date and never changed once written. The engine picks the version in
effect at a given time; the review rules apply its values, and each decision cites the
version it was decided under. A new version applies to the decisions that follow it and
never to the approvals already given.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

_POLICY_REF = re.compile(r"^pol-[A-Za-z0-9._:-]{1,124}$")
# The limits the governance contracts document (HC-131 to HC-133); a policy may only be
# stricter, never looser.
MIN_RATIONALE_LENGTH = 20
MAX_SYNC_DURATION_DAYS = 365
MAX_RESEARCH_VALIDITY_MONTHS = 12
MIN_CELL_SIZE = 10
# Consent bases of synchronization-requests.v1.yaml a policy may accept; `none` is never
# accepted.
CONSENT_BASES = ("patient_grant", "signed_consent_form", "emergency_override")


class InvalidPolicy(ValueError):
    pass


class NoPolicyInEffect(LookupError):
    pass


class ConsentMode(str, Enum):
    # The Node verifies it itself (only a patient grant, against the grants it knows).
    VERIFIED = "verified"
    # The Node cannot verify it; the reviewer confirms it outside the Node.
    MANUAL = "manual"


class PolicyStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_EFFECT = "in_effect"
    SUPERSEDED = "superseded"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidPolicy(message)


@dataclass(frozen=True)
class GovernancePolicy:
    policy_ref: str
    version: int
    effective_from: datetime
    title: str
    # Every decision.
    minimum_rationale_length: int
    # Synchronization: the longest temporary authorization, and the consent bases
    # accepted with how each is checked.
    maximum_sync_duration_days: int
    consent_bases: tuple[tuple[str, ConsentMode], ...]
    # Research: the longest validity, and the smallest output cell size allowed.
    maximum_research_validity_months: int
    minimum_cell_size: int

    def __post_init__(self) -> None:
        _require(
            bool(_POLICY_REF.fullmatch(self.policy_ref)),
            "policy_ref must be 'pol-' and an opaque suffix",
        )
        _require(self.version >= 1, "version must be at least 1")
        _require(
            self.effective_from.tzinfo is not None, "effective_from needs a UTC offset"
        )
        _require(0 < len(self.title.strip()) <= 200, "title must be 1-200 characters")
        _require(
            MIN_RATIONALE_LENGTH <= self.minimum_rationale_length <= 2000,
            f"minimum_rationale_length must be between {MIN_RATIONALE_LENGTH} and 2000",
        )
        _require(
            1 <= self.maximum_sync_duration_days <= MAX_SYNC_DURATION_DAYS,
            f"maximum_sync_duration_days must be between 1 and {MAX_SYNC_DURATION_DAYS}",
        )
        bases = [basis for basis, _ in self.consent_bases]
        _require(bool(bases), "consent_bases must accept at least one basis")
        _require(len(set(bases)) == len(bases), "consent_bases must be unique")
        for basis, mode in self.consent_bases:
            _require(basis in CONSENT_BASES, f"consent basis {basis!r} is not accepted")
            _require(
                mode is ConsentMode.MANUAL or basis == "patient_grant",
                f"the Node cannot verify {basis}; it must be manual",
            )
        _require(
            1 <= self.maximum_research_validity_months <= MAX_RESEARCH_VALIDITY_MONTHS,
            "maximum_research_validity_months must be between 1 and "
            f"{MAX_RESEARCH_VALIDITY_MONTHS}",
        )
        _require(
            self.minimum_cell_size >= MIN_CELL_SIZE,
            f"minimum_cell_size must be at least {MIN_CELL_SIZE}",
        )

    def consent_mode(self, basis: str) -> ConsentMode | None:
        """How this policy checks a consent basis; None if it does not accept it."""
        return dict(self.consent_bases).get(basis)


@dataclass(frozen=True)
class PolicyHistory:
    """Every version of the policy, in version order."""

    versions: tuple[GovernancePolicy, ...]

    def __post_init__(self) -> None:
        _require(bool(self.versions), "a policy history needs a version")
        for number, policy in enumerate(self.versions, start=1):
            _require(policy.version == number, "versions must be numbered 1, 2, ...")
        for earlier, later in zip(self.versions, self.versions[1:]):
            _require(
                earlier.effective_from < later.effective_from,
                "each version must take effect after the previous one",
            )
        refs = [p.policy_ref for p in self.versions]
        _require(len(set(refs)) == len(refs), "policy refs must be unique")

    def in_effect(self, at: datetime) -> GovernancePolicy:
        """The latest version effective at `at`."""
        effective = [p for p in self.versions if p.effective_from <= at]
        if not effective:
            raise NoPolicyInEffect(f"No governance policy is in effect at {at}.")
        return effective[-1]

    def status_at(self, policy: GovernancePolicy, at: datetime) -> PolicyStatus:
        if policy.effective_from > at:
            return PolicyStatus.SCHEDULED
        if policy == self.in_effect(at):
            return PolicyStatus.IN_EFFECT
        return PolicyStatus.SUPERSEDED

    def policy(self, policy_ref: str) -> GovernancePolicy | None:
        return next((p for p in self.versions if p.policy_ref == policy_ref), None)
