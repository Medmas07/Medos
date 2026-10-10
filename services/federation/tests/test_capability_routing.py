import pytest

from application.node_registry import NodeNotFound
from domain.federated_query import Completeness, NodeStatus, ScopeItem
from domain.node_capabilities import (
    DiscoveryOutcome,
    DiscoveryResult,
    NodeDescriptor,
    reason_not_to_ask,
)
from domain.node_capabilities import NodeStatus as DescriptorStatus
from tests.test_federate_patient_query import A, B, C, NOW, FakeNodes, federate, request

MEDS = frozenset({ScopeItem.MEDICATIONS})


def checked(outcome, scopes=(ScopeItem.MEDICATIONS,), node_ref="node-hospital-b"):
    reported = outcome in (DiscoveryOutcome.DISCOVERED, DiscoveryOutcome.INCOMPATIBLE)
    return DiscoveryResult(
        node_ref=node_ref,
        base_url="http://localhost:8102",
        outcome=outcome,
        checked_at=None if outcome is DiscoveryOutcome.NOT_CHECKED else NOW,
        detail="x",
        descriptor=NodeDescriptor(
            node_ref=node_ref,
            organization_ref="org-hospital-b",
            contract_versions=frozenset({"1.0"}),
            status=DescriptorStatus.ONLINE,
            supported_scopes=frozenset(scopes),
            mocked=False,
        )
        if reported
        else None,
    )


@pytest.mark.parametrize(
    ("result", "reason"),
    [
        (checked(DiscoveryOutcome.DISCOVERED), None),
        (
            checked(DiscoveryOutcome.DISCOVERED, scopes=(ScopeItem.ENCOUNTERS,)),
            "scope_not_supported",
        ),
        (checked(DiscoveryOutcome.INCOMPATIBLE), "incompatible"),
        (checked(DiscoveryOutcome.IDENTITY_MISMATCH), "identity_mismatch"),
        (checked(DiscoveryOutcome.NO_FEDERATION_INTERFACE), "no_federation_interface"),
        (checked(DiscoveryOutcome.UNREACHABLE), None),
        (checked(DiscoveryOutcome.INVALID_RESPONSE), None),
        (checked(DiscoveryOutcome.NOT_CHECKED), None),
    ],
    ids=lambda v: getattr(v, "outcome", v),
)
def test_only_a_check_showing_the_node_cannot_answer_stops_it(result, reason):
    assert reason_not_to_ask(result, MEDS) == reason


class FakeCapabilities:
    def __init__(self, results):
        self.results = results

    def latest(self, node_ref):
        if node_ref not in self.results:
            raise NodeNotFound(node_ref)
        return self.results[node_ref]


def test_nodes_that_cannot_answer_are_reported_not_asked_in_registry_order():
    nodes = FakeNodes({B: ()})
    capabilities = FakeCapabilities(
        {
            "node-hospital-a": checked(
                DiscoveryOutcome.NO_FEDERATION_INTERFACE, node_ref="node-hospital-a"
            ),
            "node-hospital-b": checked(
                DiscoveryOutcome.DISCOVERED, scopes=tuple(ScopeItem)
            ),
            "node-private-practice": checked(
                DiscoveryOutcome.DISCOVERED,
                scopes=(ScopeItem.MEDICATIONS,),
                node_ref="node-private-practice",
            ),
        }
    )

    result = federate(nodes, capabilities=capabilities)(request())

    assert {node for node, _ in nodes.asked} == {B}
    assert [(r.node, r.status, r.problem_code) for r in result.node_results] == [
        (A, NodeStatus.NOT_ASKED, "no_federation_interface"),
        (B, NodeStatus.OK, None),
        (C, NodeStatus.NOT_ASKED, "scope_not_supported"),
    ]
    assert result.completeness is Completeness.PARTIAL


def test_when_no_node_can_answer_none_is_asked():
    nodes = FakeNodes({})
    capabilities = FakeCapabilities(
        {
            n.node_ref: checked(DiscoveryOutcome.INCOMPATIBLE, node_ref=n.node_ref)
            for n in (A, B, C)
        }
    )
    result = federate(nodes, capabilities=capabilities)(request())
    assert nodes.asked == []
    assert {r.status for r in result.node_results} == {NodeStatus.NOT_ASKED}
    assert result.entries == ()


def test_a_node_deregistered_meanwhile_is_still_asked():
    nodes = FakeNodes({A: (), B: (), C: ()})
    federate(nodes, capabilities=FakeCapabilities({}))(request())
    assert {node for node, _ in nodes.asked} == {A, B, C}
    assert len(nodes.asked) == 3
