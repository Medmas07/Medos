import json

import pytest

from application.ai_provider import AiProviderErrorKind, AiTask
from application.explain_priority_entry import (
    TEMPLATE,
    ExplainPriorityEntry,
    TemplatePriorityExplainer,
)
from application.explanation import OUTPUT_SCHEMA
from application.model_priority_explainer import INSTRUCTIONS, ModelPriorityExplainer
from domain.explanation import GeneratorKind
from domain.priority_explanation import displayed_text, template_text
from tests.test_model_clinical_extractor import FIXED_TIME, ScriptedProvider
from tests.test_priority_explanation_domain import ENTRY, GOOD


def explain(provider):
    use_case = ExplainPriorityEntry(
        ModelPriorityExplainer(provider, new_request_id=lambda: "req-1"),
        clock=lambda: FIXED_TIME,
        new_id=lambda: "x-1",
    )
    return use_case(ENTRY)


def answer(text):
    return ScriptedProvider(text=json.dumps({"explanation": text}))


def test_checked_model_text_is_shown_without_its_citations():
    result = explain(answer(GOOD))

    assert result.explanation.text == displayed_text(GOOD)
    assert "[" not in result.explanation.text
    assert (
        result.explanation.generated_by.kind,
        result.explanation.generated_by.name,
    ) == (GeneratorKind.MODEL, "claude-agent-sdk")
    assert (result.entry_id, result.rejected_reasons) == ("queue-clin-x-1", ())
    assert result.explanation.advisory is True


def test_unsafe_model_text_is_never_returned():
    result = explain(answer(GOOD + " Cas urgent, priorité moyenne."))

    assert result.explanation.text == template_text(ENTRY)
    assert result.explanation.generated_by == TEMPLATE
    assert len(result.rejected_reasons) == 2


@pytest.mark.parametrize(
    "provider",
    [
        ScriptedProvider(error=AiProviderErrorKind.UNAVAILABLE),
        ScriptedProvider(text="not json"),
        ScriptedProvider(text=json.dumps({"text": GOOD})),
    ],
)
def test_without_usable_model_text_the_template_is_returned(provider):
    result = explain(provider)

    assert result.explanation.generated_by == TEMPLATE
    assert result.rejected_reasons[0].startswith("no model explanation:")


def test_template_mode_calls_no_model():
    result = ExplainPriorityEntry(
        TemplatePriorityExplainer(), clock=lambda: FIXED_TIME
    )(ENTRY)

    assert result.explanation.text == template_text(ENTRY)
    assert (result.rejected_reasons, result.explanation.generated_by.mocked) == (
        (),
        False,
    )


def test_sends_the_entry_without_any_patient_reference_as_an_explanation_task():
    provider = answer(GOOD)
    explain(provider)

    [request] = provider.requests
    assert (request.task, request.output_schema) == (AiTask.EXPLANATION, OUTPUT_SCHEMA)
    sent = json.loads(request.input_text)
    assert sent == {
        "rank": 1,
        "priority": "high",
        "score": 82,
        "factors": [
            {
                "ref": "F1",
                "type": "abnormal_lab",
                "label": "Résultat biologique anormal non revu",
                "severity": "high",
                "weight": None,
            },
            {
                "ref": "F2",
                "type": "missed_follow_up",
                "label": "Suivi en retard",
                "severity": "medium",
                "weight": None,
            },
        ],
        "method": {
            "kind": "deterministic_mock",
            "name": "Priorité fictive de démonstration",
            "version": "1.0",
            "description": ENTRY.method.description,
        },
    }
    # Neither the patient nor the factor ids: an id such as "alert-b-hba1c" names a test.
    assert "pat-" not in request.input_text
    assert "alert-" not in request.input_text


def test_the_instructions_keep_the_model_to_explaining():
    for phrase in (
        "the ranking\nis correct as given",
        '"priorité haute"',
        "cite each one",
        "Do not mention urgency at all",
        "not a clinical triage",
        "the decision belongs to the clinician",
        '"le patient"',
    ):
        assert phrase in INSTRUCTIONS
