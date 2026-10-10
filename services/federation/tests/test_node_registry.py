from datetime import datetime, timedelta

import pytest

from application.node_registry import (
    NodeNotFound,
    NodeRegistry,
    OrganizationAlreadyRegistered,
    RegistrationRequest,
)
from domain.federated_query import NodeRef

T0 = datetime.fromisoformat("2026-10-10T08:00:00+01:00")


class FakeStore:
    def __init__(self):
        self.items = {}

    def get(self, node_ref):
        return self.items.get(node_ref)

    def all(self):
        return tuple(self.items.values())

    def save(self, registration):
        self.items[registration.node_ref] = registration

    def remove(self, node_ref):
        del self.items[node_ref]


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now


def request(
    node="node-hospital-b", organization="org-hospital-b", url="http://localhost:8102"
):
    return RegistrationRequest(
        node_ref=node,
        organization_ref=organization,
        base_url=url,
        contract_versions=frozenset({"1.0"}),
        approval_decision_ref="dec-hospital-b",
    )


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def registry(clock):
    return NodeRegistry(store=FakeStore(), clock=clock)


def test_register_then_update_keeps_the_first_registration_time(registry, clock):
    first, created = registry.register(request())
    assert created and first.registered_at == first.updated_at == T0

    clock.now = T0 + timedelta(hours=1)
    updated, created = registry.register(request(url="http://localhost:8112"))

    assert not created
    assert updated.base_url == "http://localhost:8112"
    assert (updated.registered_at, updated.updated_at) == (T0, clock.now)


def test_one_node_per_organization(registry):
    registry.register(request())
    with pytest.raises(OrganizationAlreadyRegistered) as error:
        registry.register(request(node="node-b-2"))
    assert error.value.node_ref == "node-hospital-b"
    assert [r.node_ref for r in registry.list()] == ["node-hospital-b"]


def test_list_is_ordered_and_feeds_the_federated_query(registry):
    registry.register(request())
    registry.register(request(node="node-hospital-a", organization="org-hospital-a"))
    assert registry.approved_nodes() == (
        NodeRef("org-hospital-a", "node-hospital-a"),
        NodeRef("org-hospital-b", "node-hospital-b"),
    )


def test_get_and_deregister_unknown_nodes(registry):
    with pytest.raises(NodeNotFound):
        registry.get("node-hospital-c")
    with pytest.raises(NodeNotFound):
        registry.deregister("node-hospital-c")


def test_deregistered_node_frees_its_organization(registry):
    registry.register(request())
    registry.deregister("node-hospital-b")
    assert registry.list() == ()
    assert registry.register(request(node="node-b-2"))[1]
