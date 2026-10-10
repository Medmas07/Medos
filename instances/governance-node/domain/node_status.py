from dataclasses import dataclass

SKELETON_NOTICE = (
    "Governance Node (HC-130, HC-131). Its identity is the fictional demo Governance / "
    "Ethics Authority. It serves the hospital approval API over fictional demo "
    "applications held in memory: decisions are lost on restart, and the reviewer is "
    "declared, not authenticated. Synchronization and research requests, audit, and "
    "policy evaluation (HC-132 to HC-136) are PLANNED, so it authorizes no data "
    "exchange. No persistence, no authentication, no ledger. Liveness only; not a "
    "production health check."
)


@dataclass(frozen=True)
class NodeStatus:
    node: str
    version: str
    node_ref: str
    organization_ref: str
    capabilities: tuple[str, ...]
    notice: str = SKELETON_NOTICE
