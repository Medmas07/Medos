from dataclasses import dataclass

SKELETON_NOTICE = (
    "Hospital Node runtime skeleton (HC-111). This instance holds no clinical data, "
    "has no hospital identity configured yet (HC-112), and implements no clinical, "
    "Federation, or DMI capability. Liveness only; not a production health check."
)


@dataclass(frozen=True)
class NodeStatus:
    node: str
    version: str
    capabilities: tuple[str, ...]
    notice: str = SKELETON_NOTICE
