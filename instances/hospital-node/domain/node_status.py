from dataclasses import dataclass

from domain.clinical_record import RepositorySummary

SKELETON_NOTICE = (
    "Hospital Node runtime skeleton (HC-111 to HC-113). Its hospital identity comes "
    "from fictional demo configuration. Its clinical repository is MOCKED: fictional "
    "demo records held in memory, read-only. It serves no clinical API and implements "
    "no Federation or DMI capability. Liveness only; not a production health check."
)


@dataclass(frozen=True)
class NodeStatus:
    node: str
    version: str
    node_ref: str
    organization_ref: str
    capabilities: tuple[str, ...]
    clinical_records: RepositorySummary
    notice: str = SKELETON_NOTICE
