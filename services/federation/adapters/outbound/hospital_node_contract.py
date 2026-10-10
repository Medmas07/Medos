"""Wire mapping for contracts/federation/hospital-node-federation.v1.yaml.

Shared by every HospitalNodeClient adapter: the simulated nodes now, an HTTP client in HC-145.
"""

from datetime import datetime

from application.federate_patient_query import NodeUnavailable
from domain.federated_query import Entry, NodeQuery, NodeRef, RecordType


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
