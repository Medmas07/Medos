from dataclasses import dataclass

SKELETON_NOTICE = (
    "Governance Node (HC-130 to HC-136, HC-191, HC-192, HC-211). Its identity is the "
    "fictional demo Governance / Ethics Authority. It serves the hospital approval, synchronization request, and "
    "research access request APIs, the synchronization and research authorization "
    "checks, its audit trail, its governance policy, and the proofs anchoring its "
    "decisions, over fictional demo data held in memory: requests, decisions, audit "
    "events, and proofs are lost on restart, and "
    "submitters and readers are declared or not authenticated. Reviewers are declared "
    "too unless authentication is required (`authentication`: required), when each "
    "decision needs the reviewer's password sign-in session (HC-211, D2; sessions in "
    "memory, not production identity). The policy "
    "is a fictional demo policy, not a validated legal or ethical framework. Patient "
    "grants are checked with the Hospital Node holding them over HTTP (`grants`: "
    "http), or against fictional demo grants (`grants`: fixture, MOCKED); the demo "
    "Hospital Nodes' grants are themselves MOCKED. Its audit ledger is a simulated "
    "immutable ledger in memory (MOCKED), not a blockchain; proof hashes are computed "
    "by the Node itself and not signed. No persistence; a policy-editing workflow and "
    "a real ledger are PLANNED. Liveness only; not a production health check."
)


@dataclass(frozen=True)
class NodeStatus:
    node: str
    version: str
    node_ref: str
    organization_ref: str
    capabilities: tuple[str, ...]
    notice: str = SKELETON_NOTICE
