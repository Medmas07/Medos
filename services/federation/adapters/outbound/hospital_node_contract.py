"""Wire mapping for contracts/federation/hospital-node-federation.v1.yaml.

Shared by every adapter that talks to Hospital Nodes: the simulated query nodes now, an
HTTP query client in HC-145, and the capability discovery client (HC-143).
"""

import re
from datetime import datetime

from application.discover_capabilities import InvalidDescriptor
from application.federate_patient_query import NodeUnavailable
from domain.federated_query import Entry, NodeQuery, NodeRef, RecordType, ScopeItem
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


def entries_from_wire(node: NodeRef, result: dict) -> tuple[Entry, ...]:
    """Translate a NodeQueryResult. A node may only disclose records it holds itself."""
    entries = []
    for item in result["entries"]:
        source = NodeRef(
            organization_ref=item["source"]["organization_ref"],
            node_ref=item["source"]["node_ref"],
        )
        if source != node:
            raise NodeUnavailable(
                f"{node.node_ref} returned an entry held by {source.node_ref}."
            )
        record_type = RecordType(item["record_type"])
        entries.append(
            Entry(
                entry_ref=item["entry_ref"],
                record_type=record_type,
                occurred_at=datetime.fromisoformat(item["occurred_at"]),
                source=source,
                details=item[record_type.value],
            )
        )
    return tuple(entries)


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
