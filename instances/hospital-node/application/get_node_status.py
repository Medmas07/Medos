from application.clinical_repository import ClinicalRepository
from domain.node_identity import NodeIdentity
from domain.node_status import NodeStatus

NODE_NAME = "hospital-node"
NODE_VERSION = "0.1.0"


def get_node_status(
    identity: NodeIdentity, repository: ClinicalRepository
) -> NodeStatus:
    # Capabilities are added as their APIs land (HC-114+).
    return NodeStatus(
        node=NODE_NAME,
        version=NODE_VERSION,
        node_ref=identity.node_ref,
        organization_ref=identity.organization_ref,
        capabilities=(),
        clinical_records=repository.summary(),
    )
