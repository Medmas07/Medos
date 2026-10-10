from datetime import datetime

import pytest

from domain.federated_query import (
    Completeness,
    Entry,
    FederatedResult,
    NodeRef,
    NodeResult,
    NodeStatus,
    RecordType,
    ScopeItem,
)

A = NodeRef("org-hospital-a", "node-hospital-a")
B = NodeRef("org-hospital-b", "node-hospital-b")
NOW = datetime.fromisoformat("2026-10-10T10:00:00+01:00")


def entry(node: NodeRef, ref: str, at: str) -> Entry:
    return Entry(ref, RecordType.ENCOUNTER, datetime.fromisoformat(at), node, {})


def result(*node_results: NodeResult) -> FederatedResult:
    return FederatedResult(
        query_id="q",
        patient_ref="pat-a",
        scope=frozenset({ScopeItem.ENCOUNTERS}),
        node_results=node_results,
        mocked=True,
        aggregated_at=NOW,
    )


def test_complete_only_when_every_node_answered_ok():
    ok = NodeResult(A, NodeStatus.OK)
    assert result(ok).completeness is Completeness.COMPLETE
    unavailable = NodeResult(B, NodeStatus.UNAVAILABLE, problem_code="node_unavailable")
    partial = result(ok, unavailable)
    assert partial.completeness is Completeness.PARTIAL
    assert "not evidence of absence" in partial.notice


def test_entries_are_merged_newest_first():
    merged = result(
        NodeResult(A, NodeStatus.OK, (entry(A, "a-old", "2024-03-09T22:40:00+01:00"),)),
        NodeResult(B, NodeStatus.OK, (entry(B, "b-new", "2026-05-20T14:00:00+01:00"),)),
    ).entries
    assert [e.entry_ref for e in merged] == ["b-new", "a-old"]


@pytest.mark.parametrize(
    "build",
    [
        lambda: NodeResult(
            A,
            NodeStatus.DENIED,
            (entry(A, "x", "2026-01-01T00:00:00+01:00"),),
            "authorization_denied",
        ),
        lambda: NodeResult(A, NodeStatus.UNAVAILABLE),
        lambda: NodeResult(A, NodeStatus.OK, problem_code="node_unavailable"),
        lambda: NodeResult(
            A, NodeStatus.OK, (entry(B, "x", "2026-01-01T00:00:00+01:00"),)
        ),
    ],
    ids=[
        "failed_with_entries",
        "failed_without_reason",
        "ok_with_reason",
        "foreign_entry",
    ],
)
def test_node_result_invariants(build):
    with pytest.raises(ValueError):
        build()


def test_at_least_one_node_is_asked():
    with pytest.raises(ValueError):
        result()
