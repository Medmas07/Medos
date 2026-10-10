from domain.node_identity import NodeIdentity
from domain.node_status import NodeStatus

NODE_NAME = "governance-node"
NODE_VERSION = "0.2.0"
# Governance APIs are added as their tickets land (HC-131 to HC-136).
# hospital-approval.v1: list, read, and decide hospital applications (HC-131).
CAPABILITIES: tuple[str, ...] = ("hospital_approval",)


def get_node_status(identity: NodeIdentity) -> NodeStatus:
    return NodeStatus(
        node=NODE_NAME,
        version=NODE_VERSION,
        node_ref=identity.node_ref,
        organization_ref=identity.organization_ref,
        capabilities=CAPABILITIES,
    )
