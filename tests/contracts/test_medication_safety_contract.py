"""Boundary rules of contracts/api/medication-safety/medication-safety-check.v1.yaml."""

import copy

import pytest

from conftest import load, validator

CONTRACT = load("medication-safety/medication-safety-check.v1.yaml")
OPERATION = CONTRACT["paths"]["/v1/medication-safety-checks"]["post"]
REQUEST = OPERATION["requestBody"]["content"]["application/json"]["examples"][
    "demoConflict"
]["value"]
RESULT = OPERATION["responses"]["200"]["content"]["application/json"]["examples"][
    "warningsFound"
]["value"]
result_schema = validator(CONTRACT, "#/components/schemas/SafetyCheckResult")
request_schema = validator(CONTRACT, "#/components/schemas/SafetyCheckRequest")


def changed(document, mutate):
    copied = copy.deepcopy(document)
    mutate(copied)
    return copied


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["provenance"]["engine"].update(kind="llm"),
        lambda r: r["warnings"][0]["rule_source"].update(kind="model"),
    ],
    ids=["engine", "rule_source"],
)
def test_an_llm_cannot_be_the_safety_source(mutate):
    assert not result_schema.is_valid(changed(RESULT, mutate))


def test_ai_explanation_is_optional_and_advisory():
    explanation = {
        "text": "Plain-language explanation.",
        "advisory": True,
        "generated_by": {"kind": "model", "name": "x", "version": "1", "mocked": True},
        "generated_at": "2026-10-10T10:15:00Z",
    }
    with_explanation = changed(
        RESULT, lambda r: r["warnings"][0].update(explanation=explanation)
    )
    assert result_schema.is_valid(with_explanation)

    not_advisory = changed(
        with_explanation,
        lambda r: r["warnings"][0]["explanation"].update(advisory=False),
    )
    assert not result_schema.is_valid(not_advisory)


def test_result_is_always_pending_clinician_review():
    assert not result_schema.is_valid(
        changed(RESULT, lambda r: r.update(review_status="approved"))
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(warnings=[]),
        lambda r: r.update(outcome="no_warnings_found"),
    ],
    ids=["warnings_found_without_warnings", "no_warnings_found_with_warnings"],
)
def test_outcome_must_agree_with_warnings(mutate):
    assert not result_schema.is_valid(changed(RESULT, mutate))


def test_requests_reject_names_in_references():
    assert not request_schema.is_valid(
        changed(REQUEST, lambda r: r.update(patient_ref="Jane Doe"))
    )


def test_request_with_no_current_medications_is_valid():
    assert request_schema.is_valid(
        changed(REQUEST, lambda r: r.update(current_medications=[]))
    )
