"""Boundary rules of the HC-180 Compute-to-Data execution contract."""

import copy
import pytest
from conftest import load, validator

CONTRACT = load("research/research-node-execution.v1.yaml")
POST = CONTRACT["paths"]["/v1/research-executions"]["post"]
REQUEST = POST["requestBody"]["content"]["application/json"]["examples"][
    "canonicalJob"
]["value"]
STATES = CONTRACT["paths"]["/v1/research-executions/{execution_id}"]["get"][
    "responses"
]["200"]["content"]["application/json"]["examples"]
request_schema = validator(CONTRACT, "#/components/schemas/ExecutionRequest")
execution_schema = validator(CONTRACT, "#/components/schemas/Execution")


def changed(document, mutate):
    copied = copy.deepcopy(document)
    mutate(copied)
    return copied


@pytest.mark.parametrize(
    "name", ["running", "completed", "empty", "suppressed", "denied", "failed"]
)
def test_documented_states_are_valid(name):
    assert execution_schema.is_valid(STATES[name]["value"])


@pytest.mark.parametrize(
    "document,mutate",
    [
        (
            STATES["running"]["value"],
            lambda d: d.update(result=STATES["completed"]["value"]["result"]),
        ),
        (STATES["completed"]["value"], lambda d: d.pop("result")),
        (
            STATES["completed"]["value"],
            lambda d: d.update(error=STATES["failed"]["value"]["error"]),
        ),
        (STATES["failed"]["value"], lambda d: d.pop("error")),
        (
            STATES["failed"]["value"],
            lambda d: d.update(result=STATES["completed"]["value"]["result"]),
        ),
    ],
)
def test_result_and_error_follow_status(document, mutate):
    assert not execution_schema.is_valid(changed(document, mutate))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(patient_ref="pat-a"),
        lambda r: r["data_scope"].update(patient_ids=["pat-a"]),
        lambda r: r["algorithm"].update(source_code="read_hospital_database()"),
        lambda r: r["output_policy"].update(kind="raw_records"),
        lambda r: r["output_policy"].update(require_disclosure_review=False),
    ],
)
def test_request_cannot_bypass_compute_to_data_boundary(mutate):
    assert not request_schema.is_valid(changed(REQUEST, mutate))


def test_example_reuses_canonical_fictional_entities():
    assert (REQUEST["job_ref"], REQUEST["project_ref"]) == ("job-001", "proj-001")
    assert REQUEST["target"]["organization_ref"] == "org-hospital-a"


def test_empty_and_suppressed_outputs_return_no_rows():
    assert all(
        STATES[name]["value"]["result"]["rows"] == []
        for name in ("empty", "suppressed")
    )


def test_released_result_keeps_hospital_provenance():
    provenance = STATES["completed"]["value"]["result"]["provenance"]
    assert (provenance["source_organization_ref"], provenance["source_node_ref"]) == (
        "org-hospital-a",
        "node-hospital-a",
    )
