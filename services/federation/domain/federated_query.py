from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ScopeItem(StrEnum):
    ENCOUNTERS = "encounters"
    MEDICATIONS = "medications"
    LAB_REPORTS = "lab_reports"


class RecordType(StrEnum):
    ENCOUNTER = "encounter"
    MEDICATION = "medication"
    LAB_REPORT = "lab_report"


RECORD_TYPE_FOR_SCOPE = {
    ScopeItem.ENCOUNTERS: RecordType.ENCOUNTER,
    ScopeItem.MEDICATIONS: RecordType.MEDICATION,
    ScopeItem.LAB_REPORTS: RecordType.LAB_REPORT,
}


class AuthorizationBasis(StrEnum):
    PATIENT_ACCESS_GRANT = "patient_access_grant"
    SYNCHRONIZATION_DECISION = "synchronization_decision"


class NodeStatus(StrEnum):
    OK = "ok"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    # Not asked because its latest capability check shows it cannot answer (HC-146).
    NOT_ASKED = "not_asked"


class Completeness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


@dataclass(frozen=True)
class Authorization:
    """A Governance-backed basis. A reference, not a credential; each node verifies it."""

    basis: AuthorizationBasis
    ref: str
    expires_at: datetime


@dataclass(frozen=True)
class Requester:
    organization_ref: str
    actor_ref: str


@dataclass(frozen=True)
class NodeQuery:
    query_id: str
    patient_ref: str
    scope: frozenset[ScopeItem]
    purpose: str
    requested_by: Requester
    authorization: Authorization
    # HC-214: the Governance Node's signed authorization, under a synchronization decision.
    signed_authorization: str | None = None


@dataclass(frozen=True)
class NodeRef:
    organization_ref: str
    node_ref: str


@dataclass(frozen=True)
class Entry:
    """One record disclosed by the node that holds it.

    Federation does not interpret clinical content, so `details` is carried as-is.
    """

    entry_ref: str
    record_type: RecordType
    occurred_at: datetime
    source: NodeRef
    details: Mapping[str, object] = field(compare=False)


@dataclass(frozen=True)
class NodeResult:
    node: NodeRef
    status: NodeStatus
    entries: tuple[Entry, ...] = ()
    problem_code: str | None = None
    # True when the node said it answered from fixtures rather than real local data.
    mocked: bool = False

    def __post_init__(self) -> None:
        if self.status is NodeStatus.OK:
            if self.problem_code is not None:
                raise ValueError("A node that answered ok has no problem code.")
            if any(entry.source != self.node for entry in self.entries):
                raise ValueError("A node can only disclose entries it holds.")
        elif self.entries or self.problem_code is None:
            raise ValueError(
                "A node that did not answer ok has a reason and no entries."
            )


@dataclass(frozen=True)
class FederatedResult:
    """Transient merge of node answers. Federation stores nothing."""

    query_id: str
    patient_ref: str
    scope: frozenset[ScopeItem]
    node_results: tuple[NodeResult, ...]
    mocked: bool
    aggregated_at: datetime

    def __post_init__(self) -> None:
        if not self.node_results:
            raise ValueError("At least one node must be targeted.")

    @property
    def completeness(self) -> Completeness:
        if all(result.status is NodeStatus.OK for result in self.node_results):
            return Completeness.COMPLETE
        return Completeness.PARTIAL

    @property
    def entries(self) -> tuple[Entry, ...]:
        merged = [entry for result in self.node_results for entry in result.entries]
        return tuple(sorted(merged, key=lambda e: e.occurred_at, reverse=True))

    @property
    def notice(self) -> str:
        missing = sum(r.status is not NodeStatus.OK for r in self.node_results)
        if not missing:
            return (
                "All requested sources answered. Only entries inside the "
                "authorized scope are shown."
            )
        sources = "source" if missing == 1 else "sources"
        return (
            f"Partial history: {missing} {sources} could not be reached or refused. "
            "Missing entries are not evidence of absence."
        )
