from datetime import datetime

import pytest

from application.federate_patient_query import (
    AuthorizationExpired,
    FederatedQueryRequest,
    FederatePatientQuery,
    NodeDenied,
    NodeTimeout,
    NodeUnavailable,
    GovernanceUnavailable,
    NodeAnswer,
    NoNodesRegistered,
    SyncAuthorizationDenied,
    TargetsNotAuthorized,
    UnknownTargets,
)
from domain.sync_authorization import DenialReason, SyncAuthorization
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


class FakeSyncChecker:
    def __init__(self, answer=None):
        self.answer = answer
        self.calls = []

    def check(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.answer, Exception) or self.answer is None:
            raise self.answer or AssertionError("Governance must not be asked")
        return self.answer


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
        return (
            answer
            if isinstance(answer, NodeAnswer)
            else NodeAnswer(answer, mocked=False)
        )


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


def federate(nodes, registry=None, sync=None):
    return FederatePatientQuery(
        registry=registry or FakeRegistry(),
        nodes=nodes,
        sync_authorizations=sync or FakeSyncChecker(),
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


SYNC_PURPOSE = "Continuité des soins : consultation de cardiologie"


def sync_request(targets=None, scope=frozenset({ScopeItem.MEDICATIONS})):
    return FederatedQueryRequest(
        patient_ref="pat-a",
        scope=scope,
        purpose=SYNC_PURPOSE,
        requested_by=Requester("org-hospital-a", "clin-x"),
        authorization=Authorization(
            AuthorizationBasis.SYNCHRONIZATION_DECISION,
            "dec-sync-001",
            datetime.fromisoformat("2026-11-09T10:00:00+01:00"),
        ),
        target_organization_refs=targets,
    )


def authorization(
    valid_until="2026-11-09T10:00:00+01:00", scope=(ScopeItem.MEDICATIONS,)
):
    return SyncAuthorization(
        decision_ref="dec-sync-001",
        target_organization_refs=frozenset({"org-hospital-b"}),
        scope=frozenset(scope),
        purpose=SYNC_PURPOSE,
        valid_until=datetime.fromisoformat(valid_until),
    )


def test_sync_decision_asks_only_the_targets_governance_authorizes():
    nodes = FakeNodes({B: ()})
    sync = FakeSyncChecker(authorization())

    result = federate(nodes, sync=sync)(sync_request())

    assert [node for node, _ in nodes.asked] == [B]
    assert result.completeness is Completeness.COMPLETE
    assert sync.calls == [
        {
            "decision_ref": "dec-sync-001",
            "requested_by": Requester("org-hospital-a", "clin-x"),
            "patient_ref": "pat-a",
            "scope": frozenset({ScopeItem.MEDICATIONS}),
            "purpose": SYNC_PURPOSE,
        }
    ]


@pytest.mark.parametrize(
    ("answer", "error"),
    [
        (SyncAuthorizationDenied(DenialReason.NOT_APPROVED), SyncAuthorizationDenied),
        (GovernanceUnavailable(), GovernanceUnavailable),
    ],
)
def test_no_node_is_asked_unless_governance_confirms(answer, error):
    nodes = FakeNodes({})
    with pytest.raises(error):
        federate(nodes, sync=FakeSyncChecker(answer))(sync_request())
    assert nodes.asked == []


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        (authorization(valid_until="2026-10-10T10:00:00+01:00"), DenialReason.EXPIRED),
        (authorization(scope=(ScopeItem.ENCOUNTERS,)), DenialReason.SCOPE_EXCEEDED),
    ],
    ids=["expired_answer", "narrower_scope"],
)
def test_federation_never_widens_what_governance_returned(answer, reason):
    nodes = FakeNodes({})
    with pytest.raises(SyncAuthorizationDenied) as error:
        federate(nodes, sync=FakeSyncChecker(answer))(sync_request())
    assert error.value.reason is reason
    assert nodes.asked == []


def test_requested_targets_outside_the_authorization_are_refused():
    nodes = FakeNodes({})
    with pytest.raises(TargetsNotAuthorized) as error:
        federate(nodes, sync=FakeSyncChecker(authorization()))(
            sync_request(targets=("org-hospital-b", "org-hospital-a"))
        )
    assert error.value.organization_refs == ("org-hospital-a",)
    assert nodes.asked == []


def test_authorized_target_without_a_registered_node():
    registry = FakeRegistry(nodes=(A,))
    with pytest.raises(NoNodesRegistered):
        federate(FakeNodes({}), registry, FakeSyncChecker(authorization()))(
            sync_request()
        )


def test_patient_grants_are_not_sent_to_governance():
    federate(FakeNodes({A: (), B: (), C: ()}))(request())
