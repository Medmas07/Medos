import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from application.node_failures import NodeCircuitBreaker, RetryPolicy
from application.node_registry import NodeNotFound
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
from domain.node_capabilities import DiscoveryResult, reason_not_to_ask
from domain.sync_authorization import DenialReason, SyncAuthorization


class NodeDenied(Exception):
    pass


class NodeUnavailable(Exception):
    pass


class NodeTemporarilyUnavailable(NodeUnavailable):
    """Unavailable in a way that may pass: no connection, or the node said 503."""


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


class CapabilityLookup(Protocol):
    """Latest capability check of a registered node (DiscoverNodeCapabilities, HC-143)."""

    def latest(self, node_ref: str) -> DiscoveryResult: ...


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
        # None when capabilities say nothing about the nodes asked (simulated nodes).
        capabilities: CapabilityLookup | None,
        clock: Callable[[], datetime],
        new_id: Callable[[], str] = lambda: str(uuid4()),
        # Failure handling for real node calls (HC-147); None for simulated nodes.
        retry: RetryPolicy | None = None,
        breaker: NodeCircuitBreaker | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._registry = registry
        self._nodes = nodes
        self._sync_authorizations = sync_authorizations
        self._capabilities = capabilities
        self._clock = clock
        self._new_id = new_id
        self._retry = retry
        self._breaker = breaker
        self._monotonic = monotonic
        self._sleep = sleep

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
        not_asked = {
            node: self._reason_not_to_ask(node, request.scope) for node in targets
        }
        for node in targets:
            if not_asked[node] is None and self._breaker:
                if not self._breaker.allows(node.node_ref):
                    not_asked[node] = "circuit_open"
        to_ask = [node for node in targets if not_asked[node] is None]
        answers = {}
        if to_ask:
            started = self._monotonic()
            # Nodes are asked in parallel so one slow node does not hold up the others.
            with ThreadPoolExecutor(max_workers=len(to_ask)) as pool:
                results = pool.map(lambda node: self._ask(node, query, started), to_ask)
                answers = dict(zip(to_ask, results))
        node_results = tuple(
            answers[node]
            if node in answers
            else NodeResult(node, NodeStatus.NOT_ASKED, problem_code=not_asked[node])
            for node in targets
        )
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

    def _reason_not_to_ask(
        self, node: NodeRef, scope: frozenset[ScopeItem]
    ) -> str | None:
        if self._capabilities is None:
            return None
        try:
            latest = self._capabilities.latest(node.node_ref)
        except NodeNotFound:
            return None  # Deregistered meanwhile; the node client reports it.
        return reason_not_to_ask(latest, scope)

    def _ask(self, node: NodeRef, query: NodeQuery, started: float) -> NodeResult:
        result = self._ask_with_retries(node, query, started)
        if self._breaker:
            if result.status in (NodeStatus.OK, NodeStatus.DENIED):
                self._breaker.record_answer(node.node_ref)
            else:
                self._breaker.record_failure(node.node_ref)
        return result

    def _ask_with_retries(
        self, node: NodeRef, query: NodeQuery, started: float
    ) -> NodeResult:
        attempts = 0
        while True:
            attempts += 1
            try:
                answer = self._nodes.query(node, query)
            except NodeDenied:
                return NodeResult(
                    node, NodeStatus.DENIED, problem_code="authorization_denied"
                )
            except (NodeTemporarilyUnavailable, NodeTimeout) as error:
                # Same query_id on retry, so the node can tell it is a repeat.
                elapsed = self._monotonic() - started
                if self._retry and self._retry.may_retry(attempts, elapsed):
                    self._sleep(self._retry.backoff_seconds)
                    continue
                if isinstance(error, NodeTimeout):
                    return NodeResult(
                        node, NodeStatus.TIMEOUT, problem_code="node_timeout"
                    )
                return NodeResult(
                    node, NodeStatus.UNAVAILABLE, problem_code="node_unavailable"
                )
            except NodeUnavailable:
                return NodeResult(
                    node, NodeStatus.UNAVAILABLE, problem_code="node_unavailable"
                )
            return NodeResult(
                node, NodeStatus.OK, entries=answer.entries, mocked=answer.mocked
            )
