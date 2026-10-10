from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from domain.federated_query import ScopeItem

DISCOVERY_NOTICE = (
    "Capabilities are what each node reported about itself at checked_at. A failed "
    "check means the node could not be described, not that it holds no data."
)


class NodeStatus(StrEnum):
    ONLINE = "online"
    DEGRADED = "degraded"


class DiscoveryOutcome(StrEnum):
    DISCOVERED = "discovered"
    INCOMPATIBLE = "incompatible"
    IDENTITY_MISMATCH = "identity_mismatch"
    NO_FEDERATION_INTERFACE = "no_federation_interface"
    UNREACHABLE = "unreachable"
    INVALID_RESPONSE = "invalid_response"
    NOT_CHECKED = "not_checked"


@dataclass(frozen=True)
class NodeDescriptor:
    """What a node says about itself (hospital-node-federation.v1 NodeDescriptor)."""

    node_ref: str
    organization_ref: str
    contract_versions: frozenset[str]
    status: NodeStatus
    supported_scopes: frozenset[ScopeItem]
    mocked: bool


@dataclass(frozen=True)
class DiscoveryResult:
    """The latest capability check of one node, at the base URL it was registered with."""

    node_ref: str
    base_url: str
    outcome: DiscoveryOutcome
    checked_at: datetime | None
    detail: str
    descriptor: NodeDescriptor | None = None

    def __post_init__(self) -> None:
        reported = self.outcome in (
            DiscoveryOutcome.DISCOVERED,
            DiscoveryOutcome.INCOMPATIBLE,
        )
        if reported != (self.descriptor is not None):
            raise ValueError(
                "Only discovered or incompatible results carry capabilities."
            )
        if (self.outcome is DiscoveryOutcome.NOT_CHECKED) != (self.checked_at is None):
            raise ValueError("Only an unchecked node has no check time.")


def reason_not_to_ask(
    result: DiscoveryResult, scope: frozenset[ScopeItem]
) -> str | None:
    """Why a node should not be asked for this scope, judging by its latest check.

    Only a check that shows the node cannot answer stops it from being asked. A node
    that was never checked, could not be reached, or answered badly is still asked, so
    missing or stale discovery never hides a source.
    """
    if result.outcome is DiscoveryOutcome.DISCOVERED:
        if scope <= result.descriptor.supported_scopes:
            return None
        return "scope_not_supported"
    if result.outcome in (
        DiscoveryOutcome.INCOMPATIBLE,
        DiscoveryOutcome.IDENTITY_MISMATCH,
        DiscoveryOutcome.NO_FEDERATION_INTERFACE,
    ):
        return result.outcome.value
    return None
