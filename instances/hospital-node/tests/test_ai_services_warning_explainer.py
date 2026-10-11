"""The AI Services explainer adapter against medication-warning-explanation.v1 (HC-164).

AI Services is replaced by an httpx MockTransport: a test double, not an integration.
"""

import copy
import json
from pathlib import Path

import httpx
import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from adapters.outbound.ai_services_warning_explainer import (
    EXPLANATION_PATH,
    AiServicesWarningExplainer,
)
from adapters.outbound.validated_snapshot_rules import (
    ONC_HIGH_PRIORITY_2012,
    ValidatedSnapshotRuleSource,
)
from application.check_medication_safety import ExplanationUnavailable
from domain.medication_safety import (
    Coding,
    Medication,
    MedicationStatement,
    StatementSource,
    StatementStatus,
    check_interactions,
)
from tests.test_medication_safety_domain import RULES as TEST_RULES, med, statement

CONTRACT = yaml.safe_load(
    (
        Path(__file__).resolve().parents[3]
        / "contracts/api/ai/medication-warning-explanation.v1.yaml"
    ).read_text(encoding="utf-8")
)
OPERATION = CONTRACT["paths"][EXPLANATION_PATH]["post"]
TEMPLATE_ANSWER = OPERATION["responses"]["200"]["content"]["application/json"][
    "examples"
]["template"]["value"]
request_schema = Draft202012Validator(
    {
        "$ref": "#/components/schemas/ExplanationRequest",
        "components": CONTRACT["components"],
    },
    format_checker=FormatChecker(),
)

[WARNING] = check_interactions(
    TEST_RULES, med("Alpha", "A"), (statement("s-b", med("Bêta")),)
).warnings


def answer_for(request: httpx.Request, **changes) -> dict:
    sent = json.loads(request.content)
    body = copy.deepcopy(TEMPLATE_ANSWER)
    body["warning_id"] = sent["warning"]["warning_id"]
    body.update(changes)
    return body


def explainer(handler):
    return AiServicesWarningExplainer(
        "http://ai.test/", transport=httpx.MockTransport(handler)
    )


def test_sends_only_the_warning_and_keeps_the_advisory_explanation():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=answer_for(request))

    explanation = explainer(handler).explain("warning-1", WARNING, TEST_RULES, "clin-x")

    [request] = seen
    assert str(request.url) == "http://ai.test/v1/medication-warning-explanations"
    sent = json.loads(request.content)
    assert not list(request_schema.iter_errors(sent))
    assert sent["warning"]["rule_source"]["rule_id"] == "r-ab"
    assert "patient" not in request.content.decode()
    assert explanation.text == TEMPLATE_ANSWER["explanation"]["text"]
    assert explanation.generator_kind == "deterministic_template"


def test_a_validated_source_warning_is_a_valid_explanation_request():
    rules = ValidatedSnapshotRuleSource.load(ONC_HIGH_PRIORITY_2012).rule_set()
    [warning] = check_interactions(
        rules,
        Medication("Simvastatine", Coding("urn:other", "1")),
        (
            MedicationStatement(
                "s-1",
                Medication("Clarithromycine"),
                StatementStatus.ACTIVE,
                StatementSource("org-hospital-b"),
            ),
        ),
    ).warnings
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=answer_for(request))

    explainer(handler).explain("warning-1", warning, rules, "clin-x")

    assert not [e.message for e in request_schema.iter_errors(seen[0])]
    assert seen[0]["warning"]["severity"] == "contraindicated"


def broken_explanation(**changes):
    def handler(request):
        body = answer_for(request)
        body["explanation"].update(changes)
        return httpx.Response(200, json=body)

    return handler


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(503, json={"code": "x"}),
        lambda r: httpx.Response(200, text="not json"),
        lambda r: httpx.Response(200, json=answer_for(r, warning_id="warning-9")),
        lambda r: httpx.Response(200, json=answer_for(r, advisory=False)),
        broken_explanation(advisory=False),
        broken_explanation(text=" "),
        broken_explanation(
            generated_by={"kind": "llm", "name": "x", "version": "1", "mocked": False}
        ),
        broken_explanation(generated_at="2026-10-11T10:00:00"),
        lambda r: httpx.Response(200, json=[]),
    ],
    ids=[
        "http-503",
        "not-json",
        "other-warning",
        "not-advisory",
        "explanation-not-advisory",
        "empty-text",
        "unknown-generator",
        "naive-date",
        "not-an-object",
    ],
)
def test_anything_unexpected_means_no_explanation(handler):
    with pytest.raises(ExplanationUnavailable):
        explainer(handler).explain("warning-1", WARNING, TEST_RULES, "clin-x")


def test_an_unreachable_service_means_no_explanation():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ExplanationUnavailable, match="Cannot reach"):
        explainer(handler).explain("warning-1", WARNING, TEST_RULES, "clin-x")
