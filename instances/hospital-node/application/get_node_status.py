from domain.node_status import NodeStatus

NODE_NAME = "hospital-node"
NODE_VERSION = "0.1.0"


def get_node_status() -> NodeStatus:
    # Capabilities are added as their tickets land (HC-112 configuration, HC-113+ APIs).
    return NodeStatus(node=NODE_NAME, version=NODE_VERSION, capabilities=())
