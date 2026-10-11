"""Medication warning explanation over HTTP against its contract.

Template mode, and model mode with test-double providers only: no model is called.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from adapters.inbound.http.medication_explanation import create_router
from application.explain_medication_warning import ExplainMedicationWarning
from application.model_warning_explainer import ModelWarningExplainer
from tests.conftest import fixture_client
from tests.test_model_clinical_extractor import ScriptedProvider

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
CONTRACT = yaml.safe_load(
    (CONTRACTS / "api/ai/medication-warning-explanation.v1.yaml").read_text(
        encoding="utf-8"
    )
)
MEDICATION = yaml.safe_load(
    (CONTRACTS / "api/medication-safety/medication-safety-check.v1.yaml").read_text(
        encoding="utf-8"
    )
)
OPERATION = CONTRACT["paths"]["/v1/medication-warning-explanations"]["post"]
DEMO = OPERATION["requestBody"]["content"]["application/json"]["examples"][
    "coagulixDolorane"
]["value"]
EXAMPLES = OPERATION["responses"]["200"]["content"]["application/json"]["examples"]
PATH = "/v1/medication-warning-explanations"


def valid(body, contract=CONTRACT, name="ExplanationResult"):
    validator = Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": contract["components"]},
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


def model_client(provider):
    app = FastAPI()
    app.include_router(
        create_router(
            ExplainMedicationWarning(
                ModelWarningExplainer(provider), clock=lambda: datetime.now(UTC)
            )
        )
    )
    return TestClient(app)


def test_the_explanation_is_exactly_the_medication_contracts_explanation():
    assert (
        CONTRACT["components"]["schemas"]["Explanation"]
        == MEDICATION["components"]["schemas"]["Explanation"]
    )


def test_template_mode_answers_the_contract_example():
    body = valid(fixture_client().post(PATH, json=DEMO).json())

    assert without_volatile(body) == without_volatile(EXAMPLES["template"]["value"])
    # And it fits a medication safety Warning's `explanation` as is.
    valid(body["explanation"], MEDICATION, "Explanation")


def test_checked_model_text_is_returned():
    text = EXAMPLES["model"]["value"]["explanation"]["text"]

    body = valid(
        model_client(ScriptedProvider(text=json.dumps({"explanation": text})))
        .post(PATH, json=DEMO)
        .json()
    )

    assert without_volatile(body) == without_volatile(EXAMPLES["model"]["value"])


def test_rejected_model_text_is_replaced_by_the_template():
    bad = "Dolorane et Coagulix : interaction modérée. Réduire Dolorane à 500 mg."

    body = valid(
        model_client(ScriptedProvider(text=json.dumps({"explanation": bad})))
        .post(PATH, json=DEMO)
        .json()
    )

    assert without_volatile(body) == without_volatile(
        EXAMPLES["modelRejected"]["value"]
    )
    assert bad not in json.dumps(body, ensure_ascii=False)


def changed_warning(**changes):
    return {**DEMO, "warning": {**DEMO["warning"], **changes}}


@pytest.mark.parametrize(
    "body",
    [
        changed_warning(rule_source={**DEMO["warning"]["rule_source"], "kind": "llm"}),
        changed_warning(severity="critical"),
        changed_warning(type="drug_allergy"),
        changed_warning(summary=""),
        {**DEMO, "requested_by": "Dr X"},
        {**DEMO, "patient_ref": "pat-a"},
    ],
)
def test_an_invalid_request_is_a_400(body):
    response = fixture_client().post(PATH, json=body)

    assert response.status_code == 400
    assert valid(response.json(), name="Problem")["code"] == "invalid_request"


class EventLoopProvider(ScriptedProvider):
    """Like the Claude Agent SDK adapter: generate() runs its own event loop."""

    def generate(self, request):
        async def answer():
            return super(EventLoopProvider, self).generate(request)

        return asyncio.run(answer())


def test_a_provider_running_its_own_event_loop_works_through_the_route():
    text = EXAMPLES["model"]["value"]["explanation"]["text"]

    response = model_client(
        EventLoopProvider(text=json.dumps({"explanation": text}))
    ).post(PATH, json=DEMO)

    assert response.status_code == 200, response.text
    assert response.json()["explanation"]["generated_by"]["kind"] == "model"
