import pytest

from adapters.outbound.hospital_node_contract import InvalidNodeAnswer
from application.federate_patient_query import (
    FederatePatientQuery,
    NodeAnswer,
    NodeDenied,
    NodeTemporarilyUnavailable,
    NodeTimeout,
    NodeUnavailable,
)
from application.node_failures import NodeCircuitBreaker, RetryPolicy
from domain.federated_query import NodeStatus
from tests.test_federate_patient_query import (
    NOW,
    B,
    FakeRegistry,
    FakeSyncChecker,
    request,
)

POLICY = RetryPolicy(
    max_attempts=2, backoff_seconds=0.2, attempt_timeout_seconds=2, deadline_seconds=5
)


class ScriptedNodes:
    """Answers with the next scripted outcome per call."""

    mocked = False

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.query_ids = []

    def query(self, node, query):
        self.query_ids.append(query.query_id)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


def federate(nodes, breaker=None, monotonic=None, slept=None):
    return FederatePatientQuery(
        registry=FakeRegistry(nodes=(B,)),
        nodes=nodes,
        sync_authorizations=FakeSyncChecker(),
        capabilities=None,
        clock=lambda: NOW,
        retry=POLICY,
        breaker=breaker,
        monotonic=monotonic or Clock(),
        sleep=(slept.append if slept is not None else lambda seconds: None),
    )


def status(result):
    [node_result] = result.node_results
    return node_result.status, node_result.problem_code


@pytest.mark.parametrize(
    "transient",
    [NodeTemporarilyUnavailable("refused"), NodeTimeout("slow")],
    ids=["unreachable_or_503", "timeout"],
)
def test_a_transient_failure_is_retried_once_with_the_same_query_id(transient):
    nodes = ScriptedNodes(transient, NodeAnswer((), mocked=False))
    slept = []
    result = federate(nodes, slept=slept)(request())
    assert status(result) == (NodeStatus.OK, None)
    assert len(nodes.query_ids) == 2 and len(set(nodes.query_ids)) == 1
    assert slept == [0.2]


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (
            NodeTemporarilyUnavailable("refused"),
            (NodeStatus.UNAVAILABLE, "node_unavailable"),
        ),
        (NodeTimeout("slow"), (NodeStatus.TIMEOUT, "node_timeout")),
    ],
)
def test_a_persistent_failure_is_tried_twice_then_reported(failure, expected):
    nodes = ScriptedNodes(failure)
    assert status(federate(nodes)(request())) == expected
    assert len(nodes.query_ids) == 2


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (NodeDenied("no"), (NodeStatus.DENIED, "authorization_denied")),
        (NodeUnavailable("404"), (NodeStatus.UNAVAILABLE, "node_unavailable")),
        (InvalidNodeAnswer("leaky"), (NodeStatus.UNAVAILABLE, "node_unavailable")),
    ],
    ids=["refusal", "no_endpoint", "invalid_answer"],
)
def test_lasting_problems_are_not_retried(failure, expected):
    nodes = ScriptedNodes(failure)
    assert status(federate(nodes)(request())) == expected
    assert len(nodes.query_ids) == 1


def test_no_retry_once_the_deadline_cannot_fit_another_attempt():
    clock = Clock()

    class SlowThenFail(ScriptedNodes):
        def query(self, node, query):
            clock.now += 3.5  # the first attempt used most of the budget
            return super().query(node, query)

    nodes = SlowThenFail(NodeTimeout("slow"))
    assert status(federate(nodes, monotonic=clock)(request()))[0] is NodeStatus.TIMEOUT
    assert len(nodes.query_ids) == 1


def test_a_node_failing_three_queries_is_paused_then_probed_again():
    clock = Clock()
    breaker = NodeCircuitBreaker(clock, failure_threshold=3, cooldown_seconds=30)
    nodes = ScriptedNodes(NodeTemporarilyUnavailable("down"))
    query = federate(nodes, breaker=breaker)

    for _ in range(3):
        assert status(query(request()))[0] is NodeStatus.UNAVAILABLE
    calls = len(nodes.query_ids)

    assert status(query(request())) == (NodeStatus.NOT_ASKED, "circuit_open")
    assert len(nodes.query_ids) == calls  # not called while paused

    clock.now += 30
    nodes.outcomes = [NodeAnswer((), mocked=False)]
    assert status(query(request())) == (NodeStatus.OK, None)
    assert status(query(request())) == (NodeStatus.OK, None)


def test_a_refusal_is_an_answer_and_does_not_trip_the_breaker():
    breaker = NodeCircuitBreaker(Clock(), failure_threshold=1)
    federate(ScriptedNodes(NodeDenied("no")), breaker=breaker)(request())
    assert breaker.allows(B.node_ref)
