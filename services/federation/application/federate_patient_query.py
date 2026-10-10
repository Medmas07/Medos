from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from domain.federated_query import (
    Authorization,
    Entry,
    FederatedResult,
    NodeQuery,
    NodeRef,
    NodeResult,
    NodeStatus,
    Requester,
    ScopeItem,
)


class NodeDenied(Exception):
    pass


class NodeUnavailable(Exception):
    pass


class NodeTimeout(Exception):
    pass


class NoNodesRegistered(Exception):
    pass


class AuthorizationExpired(Exception):
    pass


class UnknownTargets(Exception):
    def __init__(self, organization_refs: tuple[str, ...]):
        super().__init__(", ".join(organization_refs))
        self.organization_refs = organization_refs


class NodeRegistry(Protocol):
    """Registered Hospital Nodes; implemented by application/node_registry.py."""

    def approved_nodes(self) -> tuple[NodeRef, ...]: ...


class HospitalNodeClient(Protocol):
    """Port to contracts/federation/hospital-node-federation.v1.yaml.

    Raises NodeDenied, NodeUnavailable, or NodeTimeout. Real node-to-node calls are HC-145.
    """

    mocked: bool

    def query(self, node: NodeRef, query: NodeQuery) -> tuple[Entry, ...]: ...


@dataclass(frozen=True)
class FederatedQueryRequest:
    patient_ref: str
    scope: frozenset[ScopeItem]
    purpose: str
    requested_by: Requester
    authorization: Authorization
    target_organization_refs: tuple[str, ...] | None = None


class FederatePatientQuery:
    def __init__(
        self,
        registry: NodeRegistry,
        nodes: HospitalNodeClient,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._registry = registry
        self._nodes = nodes
        self._clock = clock
        self._new_id = new_id

    def __call__(self, request: FederatedQueryRequest) -> FederatedResult:
        # Only a clearly expired authorization is refused here; every other check is the node's.
        if request.authorization.expires_at <= self._clock():
            raise AuthorizationExpired()

        targets = self._targets(request.target_organization_refs)
        query = NodeQuery(
            query_id=self._new_id(),
            patient_ref=request.patient_ref,
            scope=request.scope,
            purpose=request.purpose,
            requested_by=request.requested_by,
            authorization=request.authorization,
        )
        return FederatedResult(
            query_id=query.query_id,
            patient_ref=request.patient_ref,
            scope=request.scope,
            node_results=tuple(self._ask(node, query) for node in targets),
            mocked=self._nodes.mocked,
            aggregated_at=self._clock(),
        )

    def _targets(
        self, organization_refs: tuple[str, ...] | None
    ) -> tuple[NodeRef, ...]:
        approved = self._registry.approved_nodes()
        if not approved:
            raise NoNodesRegistered()
        if organization_refs is None:
            return approved
        by_organization = {node.organization_ref: node for node in approved}
        unknown = tuple(ref for ref in organization_refs if ref not in by_organization)
        if unknown:
            raise UnknownTargets(unknown)
        return tuple(by_organization[ref] for ref in organization_refs)

    def _ask(self, node: NodeRef, query: NodeQuery) -> NodeResult:
        try:
            entries = self._nodes.query(node, query)
        except NodeDenied:
            return NodeResult(
                node, NodeStatus.DENIED, problem_code="authorization_denied"
            )
        except NodeUnavailable:
            return NodeResult(
                node, NodeStatus.UNAVAILABLE, problem_code="node_unavailable"
            )
        except NodeTimeout:
            return NodeResult(node, NodeStatus.TIMEOUT, problem_code="node_timeout")
        return NodeResult(node, NodeStatus.OK, entries=entries)
