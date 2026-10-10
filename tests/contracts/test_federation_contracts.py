"""Boundary rules of the Federation contracts in contracts/federation/."""

import copy
import json
from pathlib import Path

import pytest

from conftest import FEDERATION, load, validator

NODE = load("hospital-node-federation.v1.yaml", FEDERATION)
FEDERATED = load("federated-patient-query.v1.yaml", FEDERATION)
REGISTRY = load("node-registry.v1.yaml", FEDERATION)
NODE_ONLY = {"NodeDescriptor", "NodeQueryRequest", "NodeQueryResult"}
FEDERATED_ONLY = {"FederatedQueryRequest", "FederatedQueryResult", "NodeResult"}

QUERY = FEDERATED["paths"]["/v1/federated-queries"]["post"]
REQUEST = QUERY["requestBody"]["content"]["application/json"]["examples"][
    "drXTimeline"
]["value"]
RESULT_EXAMPLES = QUERY["responses"]["200"]["content"]["application/json"]["examples"]
PARTIAL = RESULT_EXAMPLES["partialTimeline"]["value"]
result_schema = validator(FEDERATED, "#/components/schemas/FederatedQueryResult")
request_schema = validator(FEDERATED, "#/components/schemas/FederatedQueryRequest")
entry_schema = validator(FEDERATED, "#/components/schemas/Entry")

DEMO_DATA = Path(__file__).resolve().parents[2] / "demo-data"


def changed(document, mutate):
    copied = copy.deepcopy(document)
    mutate(copied)
    return copied


def _examples(contract):
    for operations in contract["paths"].values():
        for method, operation in operations.items():
            if method == "parameters":
                continue
            bodies = [operation.get("requestBody", {}).get("content", {})]
            bodies += [r.get("content", {}) for r in operation["responses"].values()]
            for content in bodies:
                for media in content.values():
                    for example in media.get("examples", {}).values():
                        yield example["value"]


def _refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("_ref") and isinstance(item, str):
                yield item
            elif key.endswith("_refs"):
                yield from item
            else:
                yield from _refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _refs(item)


def _demo_ids():
    ids = set()

    def collect(value):
        if isinstance(value, dict):
            ids.update(v for k, v in value.items() if k == "id" and isinstance(v, str))
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    for path in DEMO_DATA.rglob("*.json"):
        collect(json.loads(path.read_text()))
    return ids


def test_shared_schemas_are_identical_in_both_contracts():
    node = {
        k: v for k, v in NODE["components"]["schemas"].items() if k not in NODE_ONLY
    }
    federated = {
        k: v
        for k, v in FEDERATED["components"]["schemas"].items()
        if k not in FEDERATED_ONLY
    }
    assert node == federated


def test_examples_reference_only_canonical_demo_ids():
    known = _demo_ids()
    for contract in (NODE, FEDERATED, REGISTRY):
        for example in _examples(contract):
            unknown = set(_refs(example)) - known
            assert not unknown, f"not in demo-data: {unknown}"


@pytest.mark.parametrize("name", RESULT_EXAMPLES)
def test_entries_come_only_from_nodes_that_answered(name):
    result = RESULT_EXAMPLES[name]["value"]
    counts = {
        node["organization_ref"]: node["entry_count"]
        for node in result["node_results"]
        if node["status"] == "ok"
    }
    seen = {}
    for entry in result["entries"]:
        organization = entry["source"]["organization_ref"]
        assert organization in counts, f"{entry['entry_ref']} from a node without ok"
        seen[organization] = seen.get(organization, 0) + 1
    assert seen == {k: v for k, v in counts.items() if v}


@pytest.mark.parametrize("name", RESULT_EXAMPLES)
def test_entries_are_newest_first(name):
    entries = RESULT_EXAMPLES[name]["value"]["entries"]
    times = [entry["occurred_at"] for entry in entries]
    assert times == sorted(times, reverse=True)


def test_a_result_with_a_missing_node_cannot_be_complete():
    assert not result_schema.is_valid(
        changed(PARTIAL, lambda r: r.update(completeness="complete"))
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["node_results"][2].update(entry_count=1),
        lambda r: r["node_results"][2].update(problem_code=None),
        lambda r: r["node_results"][0].update(problem_code="node_unavailable"),
    ],
    ids=["entries_from_failed_node", "failure_without_reason", "ok_with_problem"],
)
def test_node_status_agrees_with_entries_and_problem(mutate):
    assert not result_schema.is_valid(changed(PARTIAL, mutate))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.update(record_type="encounter"),
        lambda e: e.update(encounter={"type": "x", "title": "x", "clinician_ref": "c"}),
        lambda e: e.pop("source"),
    ],
    ids=["type_mismatch", "two_bodies", "no_source"],
)
def test_an_entry_has_one_typed_body_and_a_source(mutate):
    medication_entry = PARTIAL["entries"][1]
    assert entry_schema.is_valid(medication_entry)
    assert not entry_schema.is_valid(changed(medication_entry, mutate))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.pop("authorization"),
        lambda r: r["authorization"].update(basis="platform_approval"),
        lambda r: r.update(scope=[]),
        lambda r: r.update(scope=["full_record"]),
        lambda r: r.pop("purpose"),
        lambda r: r.update(patient_ref="Patient A"),
    ],
    ids=[
        "no_authorization",
        "non_governance_basis",
        "empty_scope",
        "unknown_scope",
        "no_purpose",
        "name_in_reference",
    ],
)
def test_requests_must_be_authorized_scoped_and_minimised(mutate):
    assert request_schema.is_valid(REQUEST)
    assert not request_schema.is_valid(changed(REQUEST, mutate))
