from datetime import datetime

import pytest

from application.discover_capabilities import (
    DiscoverNodeCapabilities,
    InvalidDescriptor,
    NodeUnreachable,
    NoFederationInterface,
)
from application.node_registry import NodeNotFound, NodeRegistry, RegistrationRequest
from domain.federated_query import ScopeItem
from domain.node_capabilities import (
    DiscoveryOutcome,
    DiscoveryResult,
    NodeDescriptor,
    NodeStatus,
)
from tests.test_node_registry import FakeStore

NOW = datetime.fromisoformat("2026-10-10T10:00:00+01:00")
B_URL = "http://localhost:8102"


def descriptor(
    node="node-hospital-b", organization="org-hospital-b", versions=("1.0",)
):
    return NodeDescriptor(
        node_ref=node,
        organization_ref=organization,
        contract_versions=frozenset(versions),
        status=NodeStatus.ONLINE,
        supported_scopes=frozenset({ScopeItem.MEDICATIONS}),
        mocked=True,
    )


class FakeClient:
    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    def describe(self, base_url):
        self.asked.append(base_url)
        answer = self.answers[base_url]
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeResults:
    def __init__(self):
        self.items = {}

    def get(self, node_ref):
        return self.items.get(node_ref)

    def save(self, result):
        self.items[result.node_ref] = result


def setup(answers, url=B_URL):
    registry = NodeRegistry(store=FakeStore(), clock=lambda: NOW)
    register(registry, url)
    client = FakeClient(answers)
    return (
        registry,
        client,
        DiscoverNodeCapabilities(registry, client, FakeResults(), lambda: NOW),
    )


def register(registry, url):
    registry.register(
        RegistrationRequest(
            node_ref="node-hospital-b",
            organization_ref="org-hospital-b",
            base_url=url,
            contract_versions=frozenset({"1.0"}),
            approval_decision_ref="dec-hospital-b",
        )
    )


def test_discovered_capabilities_are_kept():
    _, client, discovery = setup({B_URL: descriptor()})
    result = discovery.discover("node-hospital-b")
    assert result.outcome is DiscoveryOutcome.DISCOVERED
    assert result.descriptor == descriptor()
    assert discovery.latest("node-hospital-b") == result
    assert client.asked == [B_URL]


@pytest.mark.parametrize(
    ("answer", "outcome"),
    [
        (NodeUnreachable("down"), DiscoveryOutcome.UNREACHABLE),
        (NoFederationInterface("404"), DiscoveryOutcome.NO_FEDERATION_INTERFACE),
        (InvalidDescriptor("bad"), DiscoveryOutcome.INVALID_RESPONSE),
    ],
)
def test_failures_are_reported_without_capabilities(answer, outcome):
    _, _, discovery = setup({B_URL: answer})
    result = discovery.discover("node-hospital-b")
    assert (result.outcome, result.descriptor, result.detail) == (
        outcome,
        None,
        str(answer),
    )


@pytest.mark.parametrize(
    "claimed",
    [descriptor(node="node-hospital-a"), descriptor(organization="org-hospital-a")],
    ids=["other_node", "other_organization"],
)
def test_identity_mismatch_drops_claimed_capabilities(claimed):
    _, _, discovery = setup({B_URL: claimed})
    result = discovery.discover("node-hospital-b")
    assert result.outcome is DiscoveryOutcome.IDENTITY_MISMATCH
    assert result.descriptor is None


def test_incompatible_node_keeps_what_it_reported():
    _, _, discovery = setup({B_URL: descriptor(versions=("2.0",))})
    result = discovery.discover("node-hospital-b")
    assert result.outcome is DiscoveryOutcome.INCOMPATIBLE
    assert result.descriptor.contract_versions == {"2.0"}


def test_result_no_longer_applies_after_the_url_changes():
    registry, _, discovery = setup({B_URL: descriptor()})
    assert discovery.latest("node-hospital-b").outcome is DiscoveryOutcome.NOT_CHECKED
    discovery.discover("node-hospital-b")
    register(registry, "http://localhost:8112")
    latest = discovery.latest("node-hospital-b")
    assert (latest.outcome, latest.base_url) == (
        DiscoveryOutcome.NOT_CHECKED,
        "http://localhost:8112",
    )


def test_unregistered_nodes_are_not_found():
    _, client, discovery = setup({})
    for call in (discovery.discover, discovery.latest):
        with pytest.raises(NodeNotFound):
            call("node-hospital-c")
    assert client.asked == []


def test_discover_all_asks_every_registered_node():
    _, _, discovery = setup({B_URL: descriptor()})
    assert [r.node_ref for r in discovery.discover_all()] == ["node-hospital-b"]


@pytest.mark.parametrize(
    "build",
    [
        lambda: DiscoveryResult(
            "n", B_URL, DiscoveryOutcome.UNREACHABLE, NOW, "x", descriptor()
        ),
        lambda: DiscoveryResult("n", B_URL, DiscoveryOutcome.DISCOVERED, NOW, "x"),
        lambda: DiscoveryResult("n", B_URL, DiscoveryOutcome.NOT_CHECKED, NOW, "x"),
        lambda: DiscoveryResult("n", B_URL, DiscoveryOutcome.UNREACHABLE, None, "x"),
    ],
    ids=[
        "failure_with_capabilities",
        "discovered_without",
        "unchecked_with_time",
        "checked_without_time",
    ],
)
def test_result_invariants(build):
    with pytest.raises(ValueError):
        build()
