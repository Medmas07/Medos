"""Boundary rules of contracts/api/sciagents/scientific-investigation.v1.yaml."""

import copy

import pytest

from conftest import load, validator

CONTRACT = load("sciagents/scientific-investigation.v1.yaml")
PATHS = CONTRACT["paths"]
REQUEST = PATHS["/v1/investigations"]["post"]["requestBody"]["content"][
    "application/json"
]["examples"]["demoInvestigation"]["value"]
STATES = PATHS["/v1/investigations/{investigation_id}"]["get"]["responses"]["200"][
    "content"
]["application/json"]["examples"]
COMPLETED = STATES["completed"]["value"]
FAILED = STATES["failed"]["value"]
RUNNING = STATES["running"]["value"]

investigation_schema = validator(CONTRACT, "#/components/schemas/Investigation")
request_schema = validator(CONTRACT, "#/components/schemas/InvestigationRequest")


def changed(document, mutate):
    copied = copy.deepcopy(document)
    mutate(copied)
    return copied


@pytest.mark.parametrize(
    "document, mutate",
    [
        (COMPLETED, lambda d: d.update(result=None)),
        (COMPLETED, lambda d: d.update(error=FAILED["error"])),
        (FAILED, lambda d: d.update(error=None)),
        (FAILED, lambda d: d.update(result=COMPLETED["result"])),
        (RUNNING, lambda d: d.update(result=COMPLETED["result"])),
        (RUNNING, lambda d: d.update(error=FAILED["error"])),
    ],
    ids=[
        "completed_without_result",
        "completed_with_error",
        "failed_without_error",
        "failed_with_result",
        "running_with_result",
        "running_with_error",
    ],
)
def test_result_and_error_follow_status(document, mutate):
    assert not investigation_schema.is_valid(changed(document, mutate))


def test_results_are_research_use_only():
    assert not investigation_schema.is_valid(
        changed(COMPLETED, lambda d: d.update(clinical_use="clinical_decision_support"))
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(patient_ref="patient-a"),
        lambda r: r.update(controlled_results=[{"summary": "patient data"}]),
        lambda r: r["concepts"][0].update(patient_ref="patient-a"),
        lambda r: r.update(concepts=[{"label": "only-one"}]),
        lambda r: r.update(
            concepts=[{"label": "one"}, {"label": "two"}, {"label": "three"}]
        ),
        lambda r: r.update(requested_by="Aymen Researcher"),
    ],
    ids=[
        "patient_reference",
        "controlled_result_content",
        "patient_reference_in_concept",
        "one_concept",
        "three_concepts",
        "name_as_reference",
    ],
)
def test_requests_cannot_carry_clinical_or_identifying_data(mutate):
    assert not request_schema.is_valid(changed(REQUEST, mutate))


def test_minimal_request_is_valid():
    minimal = {
        k: REQUEST[k]
        for k in ("project_ref", "requested_by", "question", "concepts")
    }
    assert request_schema.is_valid(minimal)


def test_contract_matches_the_upstream_keyword_pair_boundary():
    assert len(REQUEST["concepts"]) == 2
    assert [concept["label"] for concept in REQUEST["concepts"]] == [
        "Metformin",
        "Diabetes",
    ]
    assert "controlled_results" not in REQUEST


def test_contract_version_records_the_hc170_revision():
    assert CONTRACT["info"]["version"] == "1.1.0"
    assert COMPLETED["contract_version"] == "1.1"


def test_completed_result_has_explicit_findings_or_empty_outcome():
    assert COMPLETED["result"]["outcome"] == "findings"
    empty = changed(
        COMPLETED,
        lambda d: d.update(
            result={
                "outcome": "empty",
                "hypotheses": [],
                "evidence": [],
                "contradictions": [],
                "citations": [],
            }
        ),
    )
    assert investigation_schema.is_valid(empty)


def _unresolved_references(result: dict) -> set[str]:
    evidence = {e["evidence_id"] for e in result["evidence"]}
    contradictions = {c["contradiction_id"] for c in result["contradictions"]}
    citations = {c["citation_id"] for c in result["citations"]}
    missing = set()
    for hypothesis in result["hypotheses"]:
        missing |= set(hypothesis["evidence_ids"]) - evidence
        missing |= set(hypothesis["contradiction_ids"]) - contradictions
    for item in result["evidence"] + result["contradictions"]:
        missing |= set(item["citation_ids"]) - citations
    return missing


def test_example_result_references_resolve():
    assert _unresolved_references(COMPLETED["result"]) == set()


def test_reference_check_detects_dangling_citation():
    broken = changed(COMPLETED["result"], lambda r: r["citations"].pop())
    assert _unresolved_references(broken) == {"inv-001-c1"}
