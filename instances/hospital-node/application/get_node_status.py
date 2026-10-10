from application.clinical_repository import ClinicalRepository
from domain.node_identity import NodeIdentity
from domain.node_status import NodeStatus

NODE_NAME = "hospital-node"
NODE_VERSION = "0.1.0"
# hospital-node-federation.v1: describeNode and queryNode (HC-114);
# hospital-audit-events.v1: listAuditEvents (HC-116).
CAPABILITIES = ("patient_history", "audit_events")


def get_node_status(
    identity: NodeIdentity, repository: ClinicalRepository
) -> NodeStatus:
    # Capabilities are added as their APIs land.
    return NodeStatus(
        node=NODE_NAME,
        version=NODE_VERSION,
        node_ref=identity.node_ref,
        organization_ref=identity.organization_ref,
        capabilities=CAPABILITIES,
        clinical_records=repository.summary(),
    )
