from datetime import UTC, datetime

import httpx
import pytest

from sciagents_adapter import SciAgentsAdapterError, SciAgentsClient

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
INVESTIGATION_ID = "0b6f5a1e-3c2d-4e7f-9a8b-1c2d3e4f5a6b"


def request():
    return {
        "project_ref": "proj-001",
        "requested_by": "usr-aymen",
        "question": "Quelles pistes relient la metformine et le diabète ?",
        "language": "fr",
        "concepts": [{"label": "Metformin"}, {"label": "Diabetes"}],
    }


def client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(base_url="https://sciagents.invalid", transport=transport)
    return SciAgentsClient(
        "https://sciagents.invalid",
        http_client=http,
        clock=lambda: NOW,
        id_factory=lambda: INVESTIGATION_ID,
    )


def test_submit_sends_only_the_two_concepts_and_normalizes_queued_state():
    captured = {}

    def handler(upstream_request):
        captured["json"] = upstream_request.read().decode()
        return httpx.Response(202, json={"run_id": "run-abc", "status": "queued"})

    adapter = client(handler)
    result = adapter.submit(request())

    assert captured["json"] == (
        '{"keywords":["Metformin","Diabetes"],"mode":"sequential","human_review":false}'
    )
    assert result["status"] == "queued"
    assert result["provenance"] == {
        "provider": {"name": "SciAgents", "version": None},
        "adapter": {"name": "hackcure-sciagents-adapter", "version": "0.1.0"},
        "mocked": False,
        "upstream_request_ref": "run-abc",
    }
    assert "controlled_results" not in captured["json"]
    assert "question" not in captured["json"]
    assert "proj-001" not in captured["json"]


def test_inline_upstream_response_is_normalized_to_the_same_queued_boundary():
    adapter = client(lambda _: httpx.Response(200, json={"run_id": "run-inline"}))
    assert adapter.submit(request())["status"] == "queued"


def test_poll_maps_running_stage_without_inventing_percent():
    calls = 0

    def handler(upstream_request):
        nonlocal calls
        calls += 1
        if upstream_request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-abc", "status": "queued"})
        return httpx.Response(
            200,
            json={"history": [{"node": "critic"}], "evaluation": None, "error": None},
        )

    adapter = client(handler)
    investigation_id = adapter.submit(request())["investigation_id"]
    result = adapter.get(investigation_id)

    assert calls == 2
    assert result["status"] == "running"
    assert result["progress"]["stage_label"] == "Scientific critique"
    assert result["progress"]["percent"] is None


def test_poll_maps_grounded_completed_result_without_confidence_invention():
    def handler(upstream_request):
        if upstream_request.method == "POST":
            return httpx.Response(200, json={"run_id": "run-abc"})
        return httpx.Response(
            200,
            json={
                "proposal": {"hypothesis": "Metformin may affect the studied mechanism."},
                "expanded": None,
                "grounding": {
                    "citations": [
                        {
                            "claim_ref": "proposal.hypothesis",
                            "doc_id": "pmid:123",
                            "evidence_span": "Fictional evidence for adapter testing.",
                            "resolved": True,
                        },
                        {
                            "claim_ref": "proposal.mechanisms",
                            "doc_id": "invented",
                            "evidence_span": "Unresolved evidence.",
                            "resolved": False,
                        },
                    ]
                },
                "evaluation": {"passed_quality_gate": True},
                "error": None,
            },
        )

    adapter = client(handler)
    investigation_id = adapter.submit(request())["investigation_id"]
    result = adapter.get(investigation_id)

    assert result["status"] == "completed"
    assert result["result"]["outcome"] == "findings"
    hypothesis = result["result"]["hypotheses"][0]
    assert hypothesis["confidence"] is None
    assert hypothesis["contradiction_ids"] == []
    assert len(result["result"]["citations"]) == 1
    assert result["provenance"]["mocked"] is False


def test_quality_rejection_is_an_explicit_empty_completed_result():
    def handler(upstream_request):
        if upstream_request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-abc"})
        return httpx.Response(
            200,
            json={
                "proposal": {"hypothesis": "Not released."},
                "evaluation": {"passed_quality_gate": False},
                "error": None,
            },
        )

    adapter = client(handler)
    investigation_id = adapter.submit(request())["investigation_id"]
    result = adapter.get(investigation_id)
    assert result["status"] == "completed"
    assert result["result"] == {
        "outcome": "empty",
        "hypotheses": [],
        "evidence": [],
        "contradictions": [],
        "citations": [],
    }


@pytest.mark.parametrize(
    "status,code,retryable",
    [(422, "rejected_by_upstream", False), (503, "upstream_error", True)],
)
def test_submit_maps_upstream_errors(status, code, retryable):
    adapter = client(lambda _: httpx.Response(status, json={"detail": "not exposed"}))
    with pytest.raises(SciAgentsAdapterError) as caught:
        adapter.submit(request())
    assert (caught.value.code, caught.value.retryable) == (code, retryable)


def test_poll_keeps_known_run_queued_while_upstream_returns_404():
    def handler(upstream_request):
        if upstream_request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-abc"})
        return httpx.Response(404)

    adapter = client(handler)
    investigation_id = adapter.submit(request())["investigation_id"]
    assert adapter.get(investigation_id)["status"] == "queued"


def test_unknown_local_investigation_is_not_looked_up_upstream():
    adapter = client(lambda _: pytest.fail("upstream must not be called"))
    with pytest.raises(KeyError, match="investigation_not_found"):
        adapter.get("missing")


def test_invalid_concept_shape_is_rejected_before_network_access():
    adapter = client(lambda _: pytest.fail("upstream must not be called"))
    invalid = request()
    invalid["concepts"] = [{"label": "only-one"}]
    with pytest.raises(ValueError, match="exactly two concepts"):
        adapter.submit(invalid)


@pytest.mark.parametrize("missing", ["project_ref", "requested_by", "question"])
def test_missing_workflow_metadata_is_rejected_before_network_access(missing):
    adapter = client(lambda _: pytest.fail("upstream must not be called"))
    invalid = request()
    invalid.pop(missing)

    with pytest.raises(ValueError, match=f"{missing} is required"):
        adapter.submit(invalid)


def test_submit_timeout_is_explicit_and_retryable():
    def timeout(upstream_request):
        raise httpx.ReadTimeout("too slow", request=upstream_request)

    adapter = client(timeout)
    with pytest.raises(SciAgentsAdapterError) as caught:
        adapter.submit(request())
    assert (caught.value.code, caught.value.retryable) == ("timeout", True)


def test_invalid_upstream_json_becomes_explicit_failed_state():
    def handler(upstream_request):
        if upstream_request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-abc"})
        return httpx.Response(200, content=b"not-json")

    adapter = client(handler)
    investigation_id = adapter.submit(request())["investigation_id"]
    result = adapter.get(investigation_id)
    assert result["status"] == "failed"
    assert result["error"] == {
        "code": "upstream_error",
        "message": "SciAgents returned invalid JSON.",
        "retryable": False,
    }


def test_upstream_human_pause_fails_closed_at_d2():
    def handler(upstream_request):
        if upstream_request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-abc"})
        return httpx.Response(200, json={"awaiting_human": True, "error": None})

    adapter = client(handler)
    investigation_id = adapter.submit(request())["investigation_id"]
    result = adapter.get(investigation_id)
    assert result["status"] == "failed"
    assert result["error"]["retryable"] is False
    assert "human-review" in result["error"]["message"]
