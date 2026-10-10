from dataclasses import dataclass

SKELETON_NOTICE = (
    "Hospital Node runtime skeleton (HC-111, HC-112). Its hospital identity comes from "
    "fictional demo configuration. This instance holds no clinical data and implements "
    "no clinical, Federation, or DMI capability. Liveness only; not a production "
    "health check."
)


@dataclass(frozen=True)
class NodeStatus:
    node: str
    version: str
    node_ref: str
    organization_ref: str
    capabilities: tuple[str, ...]
    notice: str = SKELETON_NOTICE
