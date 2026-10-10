from dataclasses import dataclass

SKELETON_NOTICE = (
    "Governance Node (HC-130 to HC-132). Its identity is the fictional demo Governance "
    "/ Ethics Authority. It serves the hospital approval and synchronization request "
    "APIs and the synchronization authorization check over fictional demo data held "
    "in memory: requests and decisions are lost on restart, and submitters and "
    "reviewers are declared, not authenticated. Patient grants are checked against "
    "fictional demo grants (MOCKED), not the Hospital Nodes' own. Research requests, "
    "audit, and policy evaluation (HC-133 to HC-136) are PLANNED. No persistence, no "
    "authentication, no ledger. Liveness only; not a production health check."
)


@dataclass(frozen=True)
class NodeStatus:
    node: str
    version: str
    node_ref: str
    organization_ref: str
    capabilities: tuple[str, ...]
    notice: str = SKELETON_NOTICE
