from domain.node_identity import NodeIdentity
from domain.node_status import NodeStatus

NODE_NAME = "governance-node"
NODE_VERSION = "0.1.0"
# Governance APIs are added as their tickets land (HC-131 to HC-136); none exists yet.
CAPABILITIES: tuple[str, ...] = ()


def get_node_status(identity: NodeIdentity) -> NodeStatus:
    return NodeStatus(
        node=NODE_NAME,
        version=NODE_VERSION,
        node_ref=identity.node_ref,
        organization_ref=identity.organization_ref,
        capabilities=CAPABILITIES,
    )
