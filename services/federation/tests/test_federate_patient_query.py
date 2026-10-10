from datetime import datetime

import pytest

from application.federate_patient_query import (
    AuthorizationExpired,
    FederatedQueryRequest,
    FederatePatientQuery,
    NodeDenied,
    NodeTimeout,
    NodeUnavailable,
    NoNodesRegistered,
    UnknownTargets,
)
from domain.federated_query import (
    Authorization,
    AuthorizationBasis,
    Completeness,
    Entry,
    NodeRef,
    NodeStatus,
    RecordType,
    Requester,
    ScopeItem,
)

NOW = datetime.fromisoformat("2026-10-10T10:00:00+01:00")
A = NodeRef("org-hospital-a", "node-hospital-a")
B = NodeRef("org-hospital-b", "node-hospital-b")
C = NodeRef("org-private-practice", "node-private-practice")


class FakeRegistry:
    def __init__(self, nodes=(A, B, C)):
        self.nodes = nodes

    def approved_nodes(self):
        return self.nodes


class FakeNodes:
    mocked = False

    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    def query(self, node, query):
        self.asked.append((node, query))
        answer = self.answers[node]
        if isinstance(answer, Exception):
            raise answer
        return answer


def request(
    expires_at=datetime.fromisoformat("2026-10-24T09:00:00+01:00"), targets=None
):
    return FederatedQueryRequest(
        patient_ref="pat-a",
        scope=frozenset({ScopeItem.ENCOUNTERS}),
        purpose="Consultation de cardiologie",
        requested_by=Requester("org-hospital-a", "clin-x"),
        authorization=Authorization(
            AuthorizationBasis.PATIENT_ACCESS_GRANT, "grant-a-drx", expires_at
        ),
        target_organization_refs=targets,
    )


def federate(nodes, registry=None):
    return FederatePatientQuery(
        registry=registry or FakeRegistry(),
        nodes=nodes,
        clock=lambda: NOW,
        new_id=lambda: "query-1",
    )


def test_asks_every_approved_node_with_one_query_id_and_maps_failures():
    b_entry = Entry("enc-b", RecordType.ENCOUNTER, NOW, B, {})
    nodes = FakeNodes({A: NodeDenied(), B: (b_entry,), C: NodeTimeout()})

    result = federate(nodes)(request())

    assert [node for node, _ in nodes.asked] == [A, B, C]
    assert {query.query_id for _, query in nodes.asked} == {"query-1"}
    assert [(r.status, r.problem_code) for r in result.node_results] == [
        (NodeStatus.DENIED, "authorization_denied"),
        (NodeStatus.OK, None),
        (NodeStatus.TIMEOUT, "node_timeout"),
    ]
    assert result.entries == (b_entry,)
    assert result.completeness is Completeness.PARTIAL
    assert result.mocked is False


def test_unavailable_node_is_reported_not_hidden():
    result = federate(FakeNodes({A: (), B: (), C: NodeUnavailable()}))(request())
    assert result.node_results[2].status is NodeStatus.UNAVAILABLE
    assert result.completeness is Completeness.PARTIAL


def test_expired_authorization_asks_no_node():
    nodes = FakeNodes({})
    with pytest.raises(AuthorizationExpired):
        federate(nodes)(request(expires_at=NOW))
    assert nodes.asked == []


def test_targets_restrict_the_nodes_asked():
    nodes = FakeNodes({B: ()})
    result = federate(nodes)(request(targets=("org-hospital-b",)))
    assert [node for node, _ in nodes.asked] == [B]
    assert result.completeness is Completeness.COMPLETE


def test_unknown_or_unapproved_targets_are_rejected():
    with pytest.raises(UnknownTargets) as error:
        federate(FakeNodes({}))(request(targets=("org-hospital-c",)))
    assert error.value.organization_refs == ("org-hospital-c",)


def test_an_empty_registry_asks_no_node():
    with pytest.raises(NoNodesRegistered):
        federate(FakeNodes({}), FakeRegistry(nodes=()))(request())
