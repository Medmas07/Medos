from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from domain.federated_query import (
    Authorization,
    AuthorizationBasis,
    Entry,
    FederatedResult,
    NodeQuery,
    NodeRef,
    NodeResult,
    NodeStatus,
    Requester,
    ScopeItem,
)
from domain.sync_authorization import DenialReason, SyncAuthorization


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


class GovernanceUnavailable(Exception):
    pass


class SyncAuthorizationDenied(Exception):
    def __init__(self, reason: DenialReason):
        super().__init__(reason.value)
        self.reason = reason


class TargetsNotAuthorized(Exception):
    def __init__(self, organization_refs: tuple[str, ...]):
        super().__init__(", ".join(organization_refs))
        self.organization_refs = organization_refs


class UnknownTargets(Exception):
    def __init__(self, organization_refs: tuple[str, ...]):
        super().__init__(", ".join(organization_refs))
        self.organization_refs = organization_refs


class NodeRegistry(Protocol):
    """Registered Hospital Nodes; implemented by application/node_registry.py."""

    def approved_nodes(self) -> tuple[NodeRef, ...]: ...


class SyncAuthorizationChecker(Protocol):
    """Port to contracts/federation/sync-authorization-check.v1.yaml (Governance Node).

    Raises SyncAuthorizationDenied or GovernanceUnavailable.
    """

    def check(
        self,
        decision_ref: str,
        requested_by: Requester,
        patient_ref: str,
        scope: frozenset[ScopeItem],
        purpose: str,
    ) -> SyncAuthorization: ...


@dataclass(frozen=True)
class NodeAnswer:
    entries: tuple[Entry, ...]
    # What the node said in its provenance: it answered from fixtures.
    mocked: bool


class HospitalNodeClient(Protocol):
    """Port to contracts/federation/hospital-node-federation.v1.yaml.

    Raises NodeDenied, NodeUnavailable, or NodeTimeout. `mocked` is true when the client
    itself simulates nodes (HC-141) rather than calling them (HC-145).
    """

    mocked: bool

    def query(self, node: NodeRef, query: NodeQuery) -> NodeAnswer: ...


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
        sync_authorizations: SyncAuthorizationChecker,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._registry = registry
        self._nodes = nodes
        self._sync_authorizations = sync_authorizations
        self._clock = clock
        self._new_id = new_id

    def __call__(self, request: FederatedQueryRequest) -> FederatedResult:
        # Only a clearly expired authorization is refused here; every other check is the node's.
        if request.authorization.expires_at <= self._clock():
            raise AuthorizationExpired()

        if request.authorization.basis is AuthorizationBasis.SYNCHRONIZATION_DECISION:
            targets = self._sync_targets(request)
        else:
            targets = self._targets(request.target_organization_refs)
        query = NodeQuery(
            query_id=self._new_id(),
            patient_ref=request.patient_ref,
            scope=request.scope,
            purpose=request.purpose,
            requested_by=request.requested_by,
            authorization=request.authorization,
        )
        # Nodes are asked in parallel so one slow node does not hold up the others.
        with ThreadPoolExecutor(max_workers=len(targets)) as pool:
            node_results = tuple(pool.map(lambda node: self._ask(node, query), targets))
        return FederatedResult(
            query_id=query.query_id,
            patient_ref=request.patient_ref,
            scope=request.scope,
            node_results=node_results,
            mocked=self._nodes.mocked or any(r.mocked for r in node_results),
            aggregated_at=self._clock(),
        )

    def _sync_targets(self, request: FederatedQueryRequest) -> tuple[NodeRef, ...]:
        # Governance decides; nothing is asked unless it confirms the authorization.
        authorization = self._sync_authorizations.check(
            decision_ref=request.authorization.ref,
            requested_by=request.requested_by,
            patient_ref=request.patient_ref,
            scope=request.scope,
            purpose=request.purpose,
        )
        reason = authorization.denial_for(request.scope, request.purpose, self._clock())
        if reason is not None:
            raise SyncAuthorizationDenied(reason)

        allowed = authorization.target_organization_refs
        if request.target_organization_refs is not None:
            outside = tuple(
                ref for ref in request.target_organization_refs if ref not in allowed
            )
            if outside:
                raise TargetsNotAuthorized(outside)
            return self._targets(request.target_organization_refs)
        registered = self._registry.approved_nodes()
        targets = tuple(node for node in registered if node.organization_ref in allowed)
        if not targets:
            raise NoNodesRegistered()
        return targets

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
            answer = self._nodes.query(node, query)
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
        return NodeResult(
            node, NodeStatus.OK, entries=answer.entries, mocked=answer.mocked
        )
