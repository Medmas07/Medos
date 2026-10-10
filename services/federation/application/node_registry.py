from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from datetime import datetime
from typing import Protocol

from domain.federated_query import NodeRef
from domain.node_registration import NodeRegistration


class NodeNotFound(Exception):
    pass


class OrganizationAlreadyRegistered(Exception):
    def __init__(self, organization_ref: str, node_ref: str):
        super().__init__(f"{organization_ref} is already served by {node_ref}.")
        self.organization_ref = organization_ref
        self.node_ref = node_ref


class RegistrationStore(Protocol):
    """Port to wherever registrations are kept. Holds routing data, never clinical data."""

    def get(self, node_ref: str) -> NodeRegistration | None: ...

    def all(self) -> tuple[NodeRegistration, ...]: ...

    def save(self, registration: NodeRegistration) -> None: ...

    def remove(self, node_ref: str) -> None: ...


@dataclass(frozen=True)
class RegistrationRequest:
    node_ref: str
    organization_ref: str
    base_url: str
    contract_versions: frozenset[str]
    approval_decision_ref: str


class NodeRegistry:
    """Federation's node directory. Implements the NodeRegistry port of FederatePatientQuery."""

    def __init__(self, store: RegistrationStore, clock: Callable[[], datetime]) -> None:
        self._store = store
        self._clock = clock
        # Uniqueness check and save must not interleave across request threads.
        self._writes = Lock()

    def register(self, request: RegistrationRequest) -> tuple[NodeRegistration, bool]:
        """Register or update a node. Returns the registration and whether it is new."""
        with self._writes:
            return self._register(request)

    def _register(self, request: RegistrationRequest) -> tuple[NodeRegistration, bool]:
        for other in self._store.all():
            if (
                other.organization_ref == request.organization_ref
                and other.node_ref != request.node_ref
            ):
                raise OrganizationAlreadyRegistered(
                    request.organization_ref, other.node_ref
                )
        existing = self._store.get(request.node_ref)
        now = self._clock()
        registration = NodeRegistration(
            node_ref=request.node_ref,
            organization_ref=request.organization_ref,
            base_url=request.base_url,
            contract_versions=request.contract_versions,
            approval_decision_ref=request.approval_decision_ref,
            registered_at=existing.registered_at if existing else now,
            updated_at=now,
        )
        self._store.save(registration)
        return registration, existing is None

    def get(self, node_ref: str) -> NodeRegistration:
        registration = self._store.get(node_ref)
        if registration is None:
            raise NodeNotFound(node_ref)
        return registration

    def list(self) -> tuple[NodeRegistration, ...]:
        return tuple(sorted(self._store.all(), key=lambda r: r.node_ref))

    def deregister(self, node_ref: str) -> None:
        with self._writes:
            self.get(node_ref)
            self._store.remove(node_ref)

    def approved_nodes(self) -> tuple[NodeRef, ...]:
        # "Approved" means registered with an approval reference; not yet verified (HC-131).
        return tuple(registration.node for registration in self.list())
