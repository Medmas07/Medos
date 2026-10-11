"""Priority queue explanation over HTTP against its contract.

Template mode, and model mode with test-double providers only: no model is called.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from adapters.inbound.http.priority_explanation import create_router
from application.explain_priority_entry import ExplainPriorityEntry
from application.model_priority_explainer import ModelPriorityExplainer
from tests.conftest import fixture_client
from tests.test_model_clinical_extractor import ScriptedProvider
from tests.test_priority_explanation_domain import GOOD

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
CONTRACT = yaml.safe_load(
    (CONTRACTS / "api/ai/priority-queue-explanation.v1.yaml").read_text(
        encoding="utf-8"
    )
)
MEDICATION = yaml.safe_load(
    (CONTRACTS / "api/medication-safety/medication-safety-check.v1.yaml").read_text(
        encoding="utf-8"
    )
)
OPERATION = CONTRACT["paths"]["/v1/priority-queue-explanations"]["post"]
DEMO = OPERATION["requestBody"]["content"]["application/json"]["examples"][
    "demoQueueFirstEntry"
]["value"]
EXAMPLES = OPERATION["responses"]["200"]["content"]["application/json"]["examples"]
PATH = "/v1/priority-queue-explanations"
DEMO_DATA = Path(__file__).resolve().parents[3] / "demo-data" / "clinician.json"


def valid(body, name="ExplanationResult"):
    validator = Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": CONTRACT["components"]},
        format_checker=FormatChecker(),
    )
    errors = list(validator.iter_errors(body))
    assert not errors, errors[0].message
    return body


def without_volatile(body):
    body = json.loads(json.dumps(body))
    body.pop("explanation_id")
    body["explanation"].pop("generated_at")
    return body


def model_client(text):
    app = FastAPI()
    app.include_router(
        create_router(
            ExplainPriorityEntry(
                ModelPriorityExplainer(
                    ScriptedProvider(text=json.dumps({"explanation": text}))
                ),
                clock=lambda: datetime.now(UTC),
            )
        )
    )
    return TestClient(app)


def test_the_request_example_is_the_canonical_demo_queue_entry():
    demo = json.loads(DEMO_DATA.read_text(encoding="utf-8"))
    [queued] = [
        q for q in demo["priorityQueue"] if q["id"] == DEMO["entry"]["entry_id"]
    ]
    entry = DEMO["entry"]

    assert (entry["rank"], entry["priority"], entry["score"]) == (
        queued["rank"],
        queued["priority"],
        queued["score"],
    )
    assert [f["factor_id"] for f in entry["factors"]] == queued["alertIds"]
    assert [f["label"] for f in entry["factors"]] == queued["reasons"]
    assert entry["method"]["kind"] == demo["priorityMethod"]["type"]


def test_the_explanation_has_the_shape_of_the_medication_contracts_explanation():
    assert (
        CONTRACT["components"]["schemas"]["Explanation"]["properties"]
        == MEDICATION["components"]["schemas"]["Explanation"]["properties"]
    )


def test_template_mode_answers_the_contract_example():
    body = valid(fixture_client().post(PATH, json=DEMO).json())

    assert without_volatile(body) == without_volatile(EXAMPLES["template"]["value"])


def test_checked_model_text_is_returned_without_its_citations():
    body = valid(model_client(GOOD).post(PATH, json=DEMO).json())

    assert without_volatile(body) == without_volatile(EXAMPLES["model"]["value"])


def test_rejected_model_text_is_replaced_by_the_template():
    bad = (
        "Priorité moyenne : l'HbA1c à 8,9 % suggère un diabète mal contrôlé "
        "[F1], avec un suivi en retard [F2]. Voir ce patient "
        "en urgence."
    )

    body = valid(model_client(bad).post(PATH, json=DEMO).json())

    assert without_volatile(body) == without_volatile(
        EXAMPLES["modelRejected"]["value"]
    )
    assert "8,9" not in json.dumps(body, ensure_ascii=False)


def changed_entry(**changes):
    return {**DEMO, "entry": {**DEMO["entry"], **changes}}


FACTOR = DEMO["entry"]["factors"][0]


@pytest.mark.parametrize(
    "body",
    [
        changed_entry(method={**DEMO["entry"]["method"], "kind": "llm"}),
        changed_entry(priority="critical"),
        changed_entry(rank=0),
        changed_entry(factors=[]),
        changed_entry(factors=[FACTOR, FACTOR]),
        changed_entry(factors=[{**FACTOR, "type": "diagnosis"}]),
        changed_entry(factors=[{**FACTOR, "label": ""}]),
        changed_entry(patient_ref="pat-b"),
        {**DEMO, "requested_by": "Dr X"},
    ],
)
def test_an_invalid_request_is_a_400(body):
    response = fixture_client().post(PATH, json=body)

    assert response.status_code == 400
    assert valid(response.json(), name="Problem")["code"] == "invalid_request"
