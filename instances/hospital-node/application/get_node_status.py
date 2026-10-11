from application.clinical_repository import ClinicalRepository
from domain.node_identity import NodeIdentity
from domain.node_status import NodeStatus

NODE_NAME = "hospital-node"
NODE_VERSION = "0.4.0"
# hospital-node-federation.v1: describeNode and queryNode (HC-114);
# hospital-audit-events.v1: listAuditEvents (HC-116);
# patient-access-grants.v1: list, grant, and revoke access grants (HC-115);
# research-node-execution.v1: bounded installed aggregate and process sandbox (HC-183/HC-186);
# medication-safety-check.v1: deterministic drug-drug interaction check (HC-162).
CAPABILITIES = (
    "patient_history",
    "audit_events",
    "access_grants",
    "research_execution",
    "isolated_research_sandbox",
    "medication_safety_check",
)


def get_node_status(
    identity: NodeIdentity, repository: ClinicalRepository
) -> NodeStatus:
    # Capabilities are added as their APIs land.
    return NodeStatus(
        node=NODE_NAME,
        version=NODE_VERSION,
        node_ref=identity.node_ref,
        organization_ref=identity.organization_ref,
        capabilities=CAPABILITIES,
        clinical_records=repository.summary(),
    )
