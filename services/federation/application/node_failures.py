"""Failure handling for calls to Hospital Nodes (HC-147): bounded retries and a circuit breaker.

Both apply to real node-to-node calls only. Simulated nodes fail by fixture, not by
network, so retrying or tripping a breaker on them would only change the demo.
"""

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class RetryPolicy:
    """At most `max_attempts` calls per node and query, all within `deadline_seconds`.

    A retry starts only if a full attempt still fits in the deadline, so a federated
    query never waits longer than the deadline for a node.
    """

    max_attempts: int = 2
    backoff_seconds: float = 0.2
    attempt_timeout_seconds: float = 2.0
    deadline_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("At least one attempt is needed.")
        if self.attempt_timeout_seconds > self.deadline_seconds:
            raise ValueError("One attempt must fit in the deadline.")

    def may_retry(self, attempts_made: int, elapsed_seconds: float) -> bool:
        needed = elapsed_seconds + self.backoff_seconds + self.attempt_timeout_seconds
        return attempts_made < self.max_attempts and needed <= self.deadline_seconds


@dataclass
class _Circuit:
    consecutive_failures: int = 0
    open_until: float | None = None


class NodeCircuitBreaker:
    """Stops calling a node after repeated failed queries, for a cooldown.

    A failure is a query the node finally did not answer: unavailable, timed out, or
    answered outside the contract. A refusal (403) is an answer, not a failure. After
    the cooldown the node is asked again: an answer closes the circuit, another
    failure reopens it. State is kept in memory, per node_ref.
    """

    def __init__(
        self,
        clock: Callable[[], float],
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self._clock = clock
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._circuits: dict[str, _Circuit] = {}
        self._lock = Lock()

    def allows(self, node_ref: str) -> bool:
        with self._lock:
            circuit = self._circuits.get(node_ref)
            return (
                circuit is None
                or circuit.open_until is None
                or circuit.open_until <= self._clock()
            )

    def record_answer(self, node_ref: str) -> None:
        with self._lock:
            self._circuits.pop(node_ref, None)

    def record_failure(self, node_ref: str) -> None:
        with self._lock:
            circuit = self._circuits.setdefault(node_ref, _Circuit())
            circuit.consecutive_failures += 1
            reopening = circuit.open_until is not None
            if reopening or circuit.consecutive_failures >= self._threshold:
                circuit.open_until = self._clock() + self._cooldown
