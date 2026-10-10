from dataclasses import dataclass

SKELETON_NOTICE = (
    "Governance Node runtime skeleton (HC-130). Its identity is the fictional demo "
    "Governance / Ethics Authority. It serves no governance API yet: hospital approval, "
    "synchronization and research requests, audit, and policy evaluation (HC-131 to "
    "HC-136) are PLANNED, so it records and authorizes nothing. No persistence, no "
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
