from dataclasses import dataclass

from domain.clinical_record import RepositorySummary

SKELETON_NOTICE = (
    "Hospital Node (HC-111 to HC-116, HC-162, HC-183, HC-186). Its hospital identity comes from fictional demo "
    "configuration. Its clinical repository is MOCKED: fictional demo records held in "
    "memory, read-only. It answers patient history queries of the Federation contract; "
    "their authorization is MOCKED against fictional grants and decisions. Each query is "
    "audited in memory only: the audit trail is lost on restart and its readers are not "
    "authenticated. Patient access grants are MOCKED: kept in memory, lost on restart, "
    "and managed without authentication. The research agent runs only a bounded installed aggregate in the "
    "HC-186 restricted child process; its source repository is MOCKED and arbitrary submitted code execution "
    "is not implemented. This is not container-grade production isolation. The medication "
    "safety check is deterministic, but its rules are MOCKED: fictional, not a validated "
    "source. No DMI capability. "
    "Liveness only; not a production health check."
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
