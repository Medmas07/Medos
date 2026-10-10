from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from application.node_registry import NodeRegistry
from domain.node_capabilities import DiscoveryOutcome, DiscoveryResult, NodeDescriptor
from domain.node_registration import SUPPORTED_NODE_CONTRACT_VERSIONS, NodeRegistration


class NodeUnreachable(Exception):
    pass


class NoFederationInterface(Exception):
    pass


class InvalidDescriptor(Exception):
    pass


class NodeDescriptorClient(Protocol):
    """Port to GET /v1/federation/node of hospital-node-federation.v1.

    Raises NodeUnreachable, NoFederationInterface, or InvalidDescriptor.
    """

    def describe(self, base_url: str) -> NodeDescriptor: ...


class DiscoveryResultStore(Protocol):
    def get(self, node_ref: str) -> DiscoveryResult | None: ...

    def save(self, result: DiscoveryResult) -> None: ...


class DiscoverNodeCapabilities:
    def __init__(
        self,
        registry: NodeRegistry,
        client: NodeDescriptorClient,
        store: DiscoveryResultStore,
        clock: Callable[[], datetime],
    ) -> None:
        self._registry = registry
        self._client = client
        self._store = store
        self._clock = clock

    def discover(self, node_ref: str) -> DiscoveryResult:
        """Ask one registered node now. Raises NodeNotFound if it is not registered."""
        result = self._check(self._registry.get(node_ref))
        self._store.save(result)
        return result

    def discover_all(self) -> tuple[DiscoveryResult, ...]:
        return tuple(self.discover(r.node_ref) for r in self._registry.list())

    def latest(self, node_ref: str) -> DiscoveryResult:
        """Latest check of a registered node, or not_checked if none matches its current URL."""
        registration = self._registry.get(node_ref)
        result = self._store.get(node_ref)
        if result is None or result.base_url != registration.base_url:
            return DiscoveryResult(
                node_ref=node_ref,
                base_url=registration.base_url,
                outcome=DiscoveryOutcome.NOT_CHECKED,
                checked_at=None,
                detail="Not checked since the node was registered at this URL.",
            )
        return result

    def _check(self, registration: NodeRegistration) -> DiscoveryResult:
        def result(outcome, detail, descriptor=None):
            return DiscoveryResult(
                node_ref=registration.node_ref,
                base_url=registration.base_url,
                outcome=outcome,
                checked_at=self._clock(),
                detail=detail,
                descriptor=descriptor,
            )

        try:
            descriptor = self._client.describe(registration.base_url)
        except NodeUnreachable as error:
            return result(DiscoveryOutcome.UNREACHABLE, str(error))
        except NoFederationInterface as error:
            return result(DiscoveryOutcome.NO_FEDERATION_INTERFACE, str(error))
        except InvalidDescriptor as error:
            return result(DiscoveryOutcome.INVALID_RESPONSE, str(error))

        claimed = (descriptor.node_ref, descriptor.organization_ref)
        if claimed != (registration.node_ref, registration.organization_ref):
            # Capabilities from a node claiming another identity are not kept.
            return result(
                DiscoveryOutcome.IDENTITY_MISMATCH,
                f"The node at this URL identifies as {claimed[0]} of {claimed[1]}.",
            )
        if not descriptor.contract_versions & SUPPORTED_NODE_CONTRACT_VERSIONS:
            return result(
                DiscoveryOutcome.INCOMPATIBLE,
                "The node answers no hospital-node-federation version this service "
                f"speaks ({', '.join(sorted(SUPPORTED_NODE_CONTRACT_VERSIONS))}).",
                descriptor,
            )
        return result(
            DiscoveryOutcome.DISCOVERED,
            "Capabilities reported by the node.",
            descriptor,
        )
