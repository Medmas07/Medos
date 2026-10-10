from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from domain.federated_query import NodeRef

# hospital-node-federation versions this Federation Service can query.
SUPPORTED_NODE_CONTRACT_VERSIONS = frozenset({"1.0"})

REGISTRY_NOTICE = (
    "Routing directory only. Approval references are not verified with the "
    "Governance Node."
)


class InvalidRegistration(ValueError):
    pass


@dataclass(frozen=True)
class NodeRegistration:
    """Where to reach one organization's node. Routing data only; it approves nothing.

    `approval_decision_ref` cites the Governance decision the registration relies on.
    It is not verified until a Governance approval API exists (HC-131).
    """

    node_ref: str
    organization_ref: str
    base_url: str
    contract_versions: frozenset[str]
    approval_decision_ref: str
    registered_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        url = urlsplit(self.base_url)
        if (
            url.scheme not in ("http", "https")
            or not url.hostname
            or url.username is not None
            or url.query
            or url.fragment
        ):
            raise InvalidRegistration(
                "base_url must be an absolute http(s) URL without credentials, "
                "query, or fragment."
            )
        if not self.contract_versions & SUPPORTED_NODE_CONTRACT_VERSIONS:
            supported = ", ".join(sorted(SUPPORTED_NODE_CONTRACT_VERSIONS))
            raise InvalidRegistration(
                "No supported hospital-node-federation version in "
                f"contract_versions; supported: {supported}"
            )
        if self.updated_at < self.registered_at:
            raise InvalidRegistration("updated_at cannot precede registered_at.")

    @property
    def node(self) -> NodeRef:
        return NodeRef(organization_ref=self.organization_ref, node_ref=self.node_ref)
