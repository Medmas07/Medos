"""The demo medication interaction fixtures (HC-161) fit medication-safety-check.v1.yaml.

Each check case of demo-data/medication-rules.json becomes the request a caller would
send (the patient's active medication records, from every organization that holds
them) and the result the rules prescribe. demo-data/check_fixtures.py checks that the
result follows from the rules; this test checks that both fit the contract. The
medication code system below is a fictional local one: the terminology is OPEN.
"""

import json
from pathlib import Path

import pytest

from conftest import load, validator

DEMO_DATA = Path(__file__).resolve().parents[2] / "demo-data"
MEDICATION = json.loads((DEMO_DATA / "medication-rules.json").read_text("utf-8"))
RECORDS = [
    json.loads((DEMO_DATA / f"records/{name}.json").read_text("utf-8"))
    for name in ("hospital-a", "hospital-b", "private-practice")
]
CATALOG = {m["code"]: m for m in MEDICATION["medications"]}
RULES = {r["id"]: r for r in MEDICATION["interactionRules"]}
RULE_SET = MEDICATION["ruleSet"]
CASES = MEDICATION["checkCases"]

CONTRACT = load("medication-safety/medication-safety-check.v1.yaml")
EXPLANATION_CONTRACT = load("ai/medication-warning-explanation.v1.yaml")
request_schema = validator(CONTRACT, "#/components/schemas/SafetyCheckRequest")
result_schema = validator(CONTRACT, "#/components/schemas/SafetyCheckResult")
explanation_request_schema = validator(
    EXPLANATION_CONTRACT, "#/components/schemas/ExplanationRequest"
)


def medication(code):
    return {
        "name": CATALOG[code]["name"],
        "code": {"system": "urn:hackcure:demo:medication", "code": code},
    }


def statements(patient_id):
    return {
        record["id"]: {
            "statement_ref": record["id"],
            "medication": medication(record["medicationCode"]),
            "status": "active",
            "source": {"organization_ref": data["heldBy"]},
        }
        for data in RECORDS
        for record in data["medications"]
        if record["patientId"] == patient_id and record["status"] == "active"
    }


def request(case):
    return {
        "patient_ref": case["patientId"],
        "requested_by": "clin-x",
        "proposed_medication": medication(case["proposedMedicationCode"]),
        "current_medications": list(statements(case["patientId"]).values()),
    }


def warning(case, index, expected):
    rule = RULES[expected["ruleId"]]
    statement = statements(case["patientId"])[expected["conflictingStatementId"]]
    return {
        "warning_id": f"warning-{index + 1}",
        "type": "drug_drug_interaction",
        "severity": rule["severity"],
        "summary": rule["effect"],
        "proposed_medication": medication(case["proposedMedicationCode"]),
        "conflicting_statement_ref": statement["statement_ref"],
        "conflicting_medication": statement["medication"],
        "conflicting_source": statement["source"],
        "rule_source": {
            "kind": RULE_SET["kind"],
            "name": RULE_SET["name"],
            "version": RULE_SET["version"],
            "rule_id": rule["id"],
            "reference": None,
        },
        "explanation": None,
    }


def result(case):
    current = statements(case["patientId"])
    return {
        "check_id": "4f6b1c1e-2a8d-4c55-9a43-0d5c6f1b7e21",
        "contract_version": "1.0",
        "patient_ref": case["patientId"],
        "requested_by": "clin-x",
        "outcome": case["expectedOutcome"],
        "review_status": "pending_clinician_review",
        "notice": "Fictional demo result for clinician review.",
        "warnings": [
            warning(case, i, w) for i, w in enumerate(case["expectedWarnings"])
        ],
        "unevaluated_medications": [
            {
                "statement_ref": u["statementId"],
                "medication": current[u["statementId"]]["medication"],
                "reason": u["reason"],
            }
            for u in case["expectedUnevaluated"]
        ],
        "provenance": {
            "engine": {
                "kind": RULE_SET["kind"],
                "name": RULE_SET["name"],
                "version": RULE_SET["version"],
            },
            "mocked": True,
            "evaluated_at": "2026-10-10T10:15:00Z",
        },
    }


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_each_case_is_a_valid_request_and_result(case):
    errors = [e.message for e in request_schema.iter_errors(request(case))]
    errors += [e.message for e in result_schema.iter_errors(result(case))]
    assert not errors, errors


def test_the_cases_cover_every_outcome_and_severity():
    assert {c["expectedOutcome"] for c in CASES} == {
        "warnings_found",
        "no_warnings_found",
    }
    assert {
        RULES[w["ruleId"]]["severity"] for c in CASES for w in c["expectedWarnings"]
    } == {
        "contraindicated",
        "major",
        "moderate",
        "minor",
    }
    assert any(len(c["expectedWarnings"]) > 1 for c in CASES)
    assert any(c["expectedUnevaluated"] for c in CASES)


def test_the_demo_warning_can_be_sent_for_explanation():
    """HC-156 explains the demo warning without any patient reference."""
    [demo] = [c for c in CASES if c["id"] == "check-a-dolorane"]
    [w] = result(demo)["warnings"]
    body = {
        "requested_by": "clin-x",
        "warning": {
            key: w[key]
            for key in (
                "warning_id",
                "type",
                "severity",
                "summary",
                "proposed_medication",
                "conflicting_medication",
                "rule_source",
            )
        },
    }

    assert explanation_request_schema.is_valid(body)
    assert (w["severity"], w["conflicting_source"]["organization_ref"]) == (
        "major",
        "org-hospital-b",
    )
