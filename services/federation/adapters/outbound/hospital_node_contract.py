"""Wire mapping for contracts/federation/hospital-node-federation.v1.yaml.

Shared by every adapter that talks to Hospital Nodes: the HTTP query client (HC-145), the
simulated nodes (HC-141), and the capability discovery client (HC-143). Answers are
parsed strictly, so nothing outside the contract reaches the federated result.
"""

import json
import re
from datetime import date
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from application.discover_capabilities import InvalidDescriptor
from application.federate_patient_query import NodeAnswer, NodeUnavailable
from domain.federated_query import (
    RECORD_TYPE_FOR_SCOPE,
    Entry,
    NodeQuery,
    NodeRef,
    RecordType,
    ScopeItem,
)
from domain.node_capabilities import NodeDescriptor, NodeStatus


def query_to_wire(query: NodeQuery) -> dict:
    return {
        "query_id": query.query_id,
        "patient_ref": query.patient_ref,
        "scope": sorted(item.value for item in query.scope),
        "purpose": query.purpose,
        "requested_by": {
            "organization_ref": query.requested_by.organization_ref,
            "actor_ref": query.requested_by.actor_ref,
        },
        "authorization": {
            "basis": query.authorization.basis.value,
            "ref": query.authorization.ref,
            "expires_at": query.authorization.expires_at.isoformat(),
        },
    }


class InvalidNodeAnswer(NodeUnavailable):
    """The node answered outside the contract or about something it was not asked."""


Ref = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]
Text = Annotated[str, Field(min_length=1)]


class _Wire(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Source(_Wire):
    organization_ref: Ref
    node_ref: Ref


class _Encounter(_Wire):
    type: Text
    title: Text
    reason: str | None = None
    summary: str | None = None
    clinician_ref: Ref


class _Medication(_Wire):
    code: Text
    dosage: str | None = None
    status: Literal["active", "stopped", "unknown"]
    start_date: date
    end_date: date | None
    prescribed_by_ref: Ref | None = None


class _ReferenceRange(_Wire):
    low: float
    high: float


class _LabResult(_Wire):
    test: Text
    value: float
    unit: str
    reference_range: _ReferenceRange | None = None
    flag: Literal["low", "normal", "high"]


class _LabReport(_Wire):
    title: Text
    results: list[_LabResult]


class _EntryBase(_Wire):
    entry_ref: Ref
    occurred_at: AwareDatetime
    source: _Source


class _EncounterEntry(_EntryBase):
    record_type: Literal["encounter"]
    encounter: _Encounter


class _MedicationEntry(_EntryBase):
    record_type: Literal["medication"]
    medication: _Medication


class _LabReportEntry(_EntryBase):
    record_type: Literal["lab_report"]
    lab_report: _LabReport


class _Provenance(_Wire):
    mocked: bool
    answered_at: AwareDatetime


class _NodeQueryResult(_Wire):
    query_id: str
    contract_version: Literal["1.0"]
    node_ref: Ref
    organization_ref: Ref
    patient_ref: Ref
    entries: list[
        Annotated[
            _EncounterEntry | _MedicationEntry | _LabReportEntry,
            Field(discriminator="record_type"),
        ]
    ]
    provenance: _Provenance


def answer_from_wire(node: NodeRef, query: NodeQuery, payload: object) -> NodeAnswer:
    """Parse a NodeQueryResult strictly and check it answers what was asked."""
    try:
        # JSON mode: dates and date-times arrive as strings.
        result = _NodeQueryResult.model_validate_json(json.dumps(payload))
    except ValidationError as error:
        raise InvalidNodeAnswer(
            f"{node.node_ref} answered outside the contract."
        ) from error
    if (result.query_id, result.patient_ref) != (query.query_id, query.patient_ref):
        raise InvalidNodeAnswer(f"{node.node_ref} answered another query or patient.")
    if NodeRef(result.organization_ref, result.node_ref) != node:
        raise InvalidNodeAnswer(f"{node.node_ref} answered as another node.")
    allowed = {RECORD_TYPE_FOR_SCOPE[item] for item in query.scope}
    entries = []
    for item in result.entries:
        source = NodeRef(item.source.organization_ref, item.source.node_ref)
        if source != node:
            raise InvalidNodeAnswer(
                f"{node.node_ref} returned an entry held by {source.node_ref}."
            )
        record_type = RecordType(item.record_type)
        if record_type not in allowed:
            raise InvalidNodeAnswer(
                f"{node.node_ref} returned a {record_type.value} outside the scope."
            )
        details = getattr(item, record_type.value).model_dump(
            mode="json", exclude_none=True
        )
        if record_type is RecordType.MEDICATION:
            # Required but nullable in the contract, so it must survive exclude_none.
            end_date = item.medication.end_date
            details["end_date"] = end_date.isoformat() if end_date else None
        entries.append(
            Entry(
                entry_ref=item.entry_ref,
                record_type=record_type,
                occurred_at=item.occurred_at,
                source=source,
                details=details,
            )
        )
    return NodeAnswer(entries=tuple(entries), mocked=result.provenance.mocked)


DESCRIPTOR_FIELDS = {
    "node_ref",
    "organization_ref",
    "contract_versions",
    "status",
    "supported_scopes",
    "mocked",
}
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+$")


def descriptor_from_wire(payload: object) -> NodeDescriptor:
    """Parse a NodeDescriptor strictly; anything outside the contract is rejected."""
    if not isinstance(payload, dict) or set(payload) != DESCRIPTOR_FIELDS:
        raise InvalidDescriptor("The response is not a NodeDescriptor.")
    refs = (payload["node_ref"], payload["organization_ref"])
    versions = payload["contract_versions"]
    scopes = payload["supported_scopes"]
    if not all(isinstance(ref, str) and REF.match(ref) for ref in refs):
        raise InvalidDescriptor(
            "node_ref or organization_ref is not an opaque reference."
        )
    if (
        not isinstance(versions, list)
        or not versions
        or len(set(versions)) != len(versions)
        or not all(isinstance(v, str) and VERSION.match(v) for v in versions)
    ):
        raise InvalidDescriptor("contract_versions is invalid.")
    if not isinstance(scopes, list) or len(set(map(str, scopes))) != len(scopes):
        raise InvalidDescriptor("supported_scopes is invalid.")
    if not isinstance(payload["mocked"], bool):
        raise InvalidDescriptor("mocked must be a boolean.")
    try:
        status = NodeStatus(payload["status"])
        supported_scopes = frozenset(ScopeItem(scope) for scope in scopes)
    except ValueError as error:
        raise InvalidDescriptor(str(error)) from error
    return NodeDescriptor(
        node_ref=refs[0],
        organization_ref=refs[1],
        contract_versions=frozenset(versions),
        status=status,
        supported_scopes=supported_scopes,
        mocked=payload["mocked"],
    )
