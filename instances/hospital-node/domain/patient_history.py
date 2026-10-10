"""An authorized, scoped query about one patient's history at this node (HC-114).

Mirrors NodeQueryRequest and NodeQueryResult of
contracts/federation/hospital-node-federation.v1.yaml. The node answers only from the
records it holds, and only inside the requested scope.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from domain.clinical_record import PatientRecords
from domain.node_identity import is_opaque_ref


class InvalidHistoryQuery(ValueError):
    pass


class ScopeItem(Enum):
    ENCOUNTERS = "encounters"
    MEDICATIONS = "medications"
    LAB_REPORTS = "lab_reports"


class AuthorizationBasis(Enum):
    PATIENT_ACCESS_GRANT = "patient_access_grant"
    SYNCHRONIZATION_DECISION = "synchronization_decision"


@dataclass(frozen=True)
class Requester:
    organization_ref: str
    actor_ref: str


@dataclass(frozen=True)
class Authorization:
    """A reference to a Governance-backed basis, not a credential."""

    basis: AuthorizationBasis
    ref: str
    expires_at: datetime


@dataclass(frozen=True)
class HistoryQuery:
    query_id: str
    patient_ref: str
    scope: frozenset[ScopeItem]
    purpose: str
    requested_by: Requester
    authorization: Authorization

    def __post_init__(self) -> None:
        refs = {
            "patient_ref": self.patient_ref,
            "requested_by.organization_ref": self.requested_by.organization_ref,
            "requested_by.actor_ref": self.requested_by.actor_ref,
            "authorization.ref": self.authorization.ref,
        }
        for field, value in refs.items():
            if not is_opaque_ref(value):
                raise InvalidHistoryQuery(f"{field} must be an opaque reference")
        if not self.scope:
            raise InvalidHistoryQuery("scope must name at least one record type")
        if not self.purpose.strip():
            raise InvalidHistoryQuery("purpose must not be empty")
        if self.authorization.expires_at.tzinfo is None:
            raise InvalidHistoryQuery(
                "authorization.expires_at must include a UTC offset"
            )


def within_scope(
    records: PatientRecords, scope: frozenset[ScopeItem]
) -> PatientRecords:
    """Drop every record type the query did not ask for."""
    return PatientRecords(
        encounters=records.encounters if ScopeItem.ENCOUNTERS in scope else (),
        medications=records.medications if ScopeItem.MEDICATIONS in scope else (),
        lab_reports=records.lab_reports if ScopeItem.LAB_REPORTS in scope else (),
    )


@dataclass(frozen=True)
class PatientHistory:
    """What this node discloses. Empty means nothing was disclosed, not no history."""

    query_id: str
    patient_ref: str
    records: PatientRecords
    mocked: bool
    answered_at: datetime
