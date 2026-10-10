from dataclasses import dataclass

SKELETON_NOTICE = (
    "Governance Node (HC-130 to HC-133). Its identity is the fictional demo Governance "
    "/ Ethics Authority. It serves the hospital approval, synchronization request, and "
    "research access request APIs, and the synchronization and research authorization "
    "checks, over fictional demo data held in memory: requests and decisions are lost "
    "on restart, and submitters and reviewers are declared, not authenticated. Patient "
    "grants are checked against fictional demo grants (MOCKED), not the Hospital "
    "Nodes' own. Audit and policy evaluation (HC-134 to HC-136) are PLANNED. No "
    "persistence, no authentication, no ledger. Liveness only; not a production "
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
