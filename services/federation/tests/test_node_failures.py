import pytest

from application.node_failures import NodeCircuitBreaker, RetryPolicy


def test_retry_only_if_a_full_attempt_still_fits():
    policy = RetryPolicy(
        max_attempts=2,
        backoff_seconds=0.2,
        attempt_timeout_seconds=2,
        deadline_seconds=5,
    )
    assert policy.may_retry(attempts_made=1, elapsed_seconds=2.0)
    assert not policy.may_retry(attempts_made=1, elapsed_seconds=2.9)
    assert not policy.may_retry(attempts_made=2, elapsed_seconds=0.1)


@pytest.mark.parametrize(
    "kwargs",
    [{"max_attempts": 0}, {"attempt_timeout_seconds": 6, "deadline_seconds": 5}],
    ids=["no_attempt", "attempt_longer_than_deadline"],
)
def test_invalid_policies_are_rejected(kwargs):
    with pytest.raises(ValueError):
        RetryPolicy(**kwargs)


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


def test_circuit_opens_after_the_threshold_and_reopens_on_a_failed_probe():
    clock = Clock()
    breaker = NodeCircuitBreaker(clock, failure_threshold=3, cooldown_seconds=30)
    for _ in range(2):
        breaker.record_failure("node-b")
    assert breaker.allows("node-b")
    breaker.record_failure("node-b")
    assert not breaker.allows("node-b")

    clock.now += 30
    assert breaker.allows("node-b")  # probe after the cooldown
    breaker.record_failure("node-b")
    assert not breaker.allows("node-b")  # one failed probe reopens it

    clock.now += 30
    breaker.record_answer("node-b")
    breaker.record_failure("node-b")
    assert breaker.allows("node-b")  # an answer reset the count


def test_circuits_are_per_node():
    breaker = NodeCircuitBreaker(Clock(), failure_threshold=1)
    breaker.record_failure("node-a")
    assert not breaker.allows("node-a")
    assert breaker.allows("node-b")
