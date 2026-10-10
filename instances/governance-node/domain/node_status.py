from dataclasses import dataclass

SKELETON_NOTICE = (
    "Governance Node (HC-130 to HC-135). Its identity is the fictional demo Governance "
    "/ Ethics Authority. It serves the hospital approval, synchronization request, and "
    "research access request APIs, the synchronization and research authorization "
    "checks, its audit trail, and its governance policy, over fictional demo data held "
    "in memory: requests, decisions, and audit events are lost on restart, and "
    "submitters, reviewers, and readers are declared or not authenticated. The policy "
    "is a fictional demo policy, not a validated legal or ethical framework. Patient "
    "grants are checked against fictional demo grants (MOCKED), not the Hospital "
    "Nodes' own. Consent evaluation (HC-136) is PLANNED. No persistence, no "
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
