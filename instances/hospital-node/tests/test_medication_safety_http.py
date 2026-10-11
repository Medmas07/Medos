"""Medication safety check over HTTP against its contract (HC-162).

Every check case of demo-data/medication-rules.json (HC-161) is sent the way a caller
would: the patient's active medication records from every organization that holds
them. The answer must fit the contract and match the case's expected result.
"""

import copy
import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from fastapi import FastAPI

from adapters.inbound.http.medication_safety import create_router
from adapters.outbound.fixture_interaction_rules import FixtureInteractionRuleSource
from application.check_medication_safety import (
    CheckMedicationSafety,
    RuleSourceUnavailable,
)
from infrastructure.config import load_config
from main import create_app
from tests.conftest import CONFIG_DIR, DEMO_NOW
from tests.test_check_medication_safety import ExplainerDouble

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = yaml.safe_load(
    (
        ROOT / "contracts/api/medication-safety/medication-safety-check.v1.yaml"
    ).read_text(encoding="utf-8")
)
OPERATION = CONTRACT["paths"]["/v1/medication-safety-checks"]["post"]
PATH = "/v1/medication-safety-checks"
FIXTURE = json.loads((ROOT / "demo-data/medication-rules.json").read_text("utf-8"))
RECORDS = [
    json.loads((ROOT / f"demo-data/records/{name}.json").read_text("utf-8"))
    for name in ("hospital-a", "hospital-b", "private-practice")
]
CATALOG = {m["code"]: m["name"] for m in FIXTURE["medications"]}
SYSTEM = FIXTURE["ruleSet"]["codeSystem"]
RULES = {r["id"]: r for r in FIXTURE["interactionRules"]}
CASES = FIXTURE["checkCases"]

client = TestClient(
    create_app(load_config(CONFIG_DIR / "hospital-a.demo.json"), clock=lambda: DEMO_NOW)
)


def valid(body, name="SafetyCheckResult"):
    validator = Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": CONTRACT["components"]},
        format_checker=FormatChecker(),
    )
    errors = [e.message for e in validator.iter_errors(body)]
    assert not errors, errors
    return body


def medication(code):
    return {"name": CATALOG[code], "code": {"system": SYSTEM, "code": code}}


def request_for(case):
    return {
        "patient_ref": case["patientId"],
        "encounter_ref": "enc-demo",
        "requested_by": "clin-x",
        "proposed_medication": medication(case["proposedMedicationCode"]),
        "current_medications": [
            {
                "statement_ref": record["id"],
                "medication": medication(record["medicationCode"]),
                "status": record["status"],
                "source": {"organization_ref": data["heldBy"]},
            }
            for data in RECORDS
            for record in data["medications"]
            if record["patientId"] == case["patientId"]
        ],
    }


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_each_demo_case_gives_its_expected_result(case):
    response = client.post(PATH, json=request_for(case))

    assert response.status_code == 200, response.text
    body = valid(response.json())
    assert body["outcome"] == case["expectedOutcome"]
    assert {
        (w["rule_source"]["rule_id"], w["conflicting_statement_ref"])
        for w in body["warnings"]
    } == {(w["ruleId"], w["conflictingStatementId"]) for w in case["expectedWarnings"]}
    assert {
        (u["statement_ref"], u["reason"]) for u in body["unevaluated_medications"]
    } == {(u["statementId"], u["reason"]) for u in case["expectedUnevaluated"]}
    assert body["provenance"]["mocked"] is True
    assert "MOCKED" in body["notice"]
    assert body["review_status"] == "pending_clinician_review"


def test_the_demo_warning_carries_its_rule_source_and_origin():
    [demo] = [c for c in CASES if c["id"] == "check-a-dolorane"]

    body = client.post(PATH, json=request_for(demo)).json()

    [warning] = body["warnings"]
    assert warning["severity"] == "major"
    assert warning["summary"] == RULES["rule-coagulix-dolorane"]["effect"]
    assert warning["conflicting_medication"]["name"] == "Coagulix"
    assert warning["conflicting_source"] == {"organization_ref": "org-hospital-b"}
    assert warning["rule_source"] == {
        "kind": "deterministic_rule_set",
        "name": "demo-interaction-rules",
        "version": "1.0.0",
        "rule_id": "rule-coagulix-dolorane",
        "reference": None,
    }
    assert warning["explanation"] is None
    assert body["encounter_ref"] == "enc-demo"
    assert body["provenance"]["evaluated_at"] == DEMO_NOW.isoformat()


def test_names_alone_identify_medications_when_no_code_is_given():
    [demo] = [c for c in CASES if c["id"] == "check-a-fongivex"]
    body = request_for(demo)
    body["proposed_medication"]["code"] = None
    for statement in body["current_medications"]:
        statement["medication"]["code"] = None

    result = valid(client.post(PATH, json=body).json())

    assert [w["severity"] for w in result["warnings"]] == ["contraindicated", "minor"]
    assert [w["warning_id"] for w in result["warnings"]] == ["warning-1", "warning-2"]


def problem(response, status, code):
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = valid(response.json(), "Problem")
    assert body["code"] == code
    return body


def test_the_contract_example_names_no_known_medication_so_no_check_is_performed():
    """The contract's example uses generic names ("Medication B") the rules do not know."""
    example = OPERATION["requestBody"]["content"]["application/json"]["examples"][
        "demoConflict"
    ]["value"]

    body = problem(client.post(PATH, json=example), 503, "safety_check_unavailable")

    assert "No check was performed" in body["detail"]


class UnavailableRules:
    mocked = True

    def rule_set(self):
        raise RuleSourceUnavailable("gone")


def test_without_rules_the_answer_is_503_not_no_warnings():
    app = FastAPI()
    app.include_router(
        create_router(CheckMedicationSafety(UnavailableRules(), lambda: DEMO_NOW))
    )

    response = TestClient(app).post(PATH, json=request_for(CASES[0]))

    problem(response, 503, "safety_check_unavailable")


def changed(mutate):
    body = copy.deepcopy(request_for(CASES[0]))
    mutate(body)
    return body


@pytest.mark.parametrize(
    "body",
    [
        changed(lambda b: b.update(patient_ref="Leïla Mansouri")),
        changed(lambda b: b.pop("requested_by")),
        changed(lambda b: b["proposed_medication"].pop("code")),
        changed(lambda b: b["proposed_medication"].update(name="")),
        changed(lambda b: b["current_medications"][0].update(status="paused")),
        changed(
            lambda b: b["current_medications"][0]["source"].update(
                recorded_at="2026-01-01"
            )
        ),
        changed(lambda b: b.update(current_medications=b["current_medications"] * 201)),
        changed(lambda b: b.update(diagnosis="x")),
    ],
    ids=[
        "name-as-ref",
        "no-requester",
        "code-missing",
        "empty-name",
        "unknown-status",
        "date-without-offset",
        "too-many",
        "extra-field",
    ],
)
def test_a_request_outside_the_contract_is_a_400(body):
    problem(client.post(PATH, json=body), 400, "invalid_request")


def test_the_rules_are_the_demo_fixture():
    source = FixtureInteractionRuleSource.load(ROOT / "demo-data/medication-rules.json")
    assert source.rule_set().version == FIXTURE["ruleSet"]["version"]


def explained_client(explainer):
    app = FastAPI()
    app.include_router(
        create_router(
            CheckMedicationSafety(
                FixtureInteractionRuleSource.load(
                    ROOT / "demo-data/medication-rules.json"
                ),
                lambda: DEMO_NOW,
                explainer=explainer,
            )
        )
    )
    return TestClient(app)


def test_an_advisory_explanation_is_attached_to_its_warning():
    [demo] = [c for c in CASES if c["id"] == "check-a-fongivex"]
    result = valid(
        explained_client(ExplainerDouble()).post(PATH, json=request_for(demo)).json()
    )

    assert [w["explanation"]["text"] for w in result["warnings"]] == [
        "Explication de rule-coagulix-fongivex.",
        "Explication de rule-tensiorel-fongivex.",
    ]
    assert all(w["explanation"]["advisory"] is True for w in result["warnings"])
    assert "Explanations are advisory" in result["notice"]


def test_without_an_explanation_the_warning_is_complete_and_null():
    [demo] = [c for c in CASES if c["id"] == "check-a-dolorane"]
    failing = ExplainerDouble(fail_on={"rule-coagulix-dolorane"})
    result = valid(explained_client(failing).post(PATH, json=request_for(demo)).json())

    [warning] = result["warnings"]
    assert warning["explanation"] is None
    assert warning["severity"] == "major"
    assert "Explanations are advisory" not in result["notice"]
