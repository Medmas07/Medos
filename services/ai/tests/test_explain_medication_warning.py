import json

import pytest

from application.ai_provider import AiProviderErrorKind, AiTask
from application.explain_medication_warning import (
    TEMPLATE,
    ExplainMedicationWarning,
    TemplateExplainer,
)
from application.model_warning_explainer import (
    INSTRUCTIONS,
    OUTPUT_SCHEMA,
    ModelWarningExplainer,
)
from domain.medication_explanation import GeneratorKind, template_text
from tests.test_medication_explanation_domain import GOOD, WARNING
from tests.test_model_clinical_extractor import FIXED_TIME, ScriptedProvider


def explain(provider):
    use_case = ExplainMedicationWarning(
        ModelWarningExplainer(provider, new_request_id=lambda: "req-1"),
        clock=lambda: FIXED_TIME,
        new_id=lambda: "x-1",
    )
    return use_case(WARNING)


def answer(text):
    return ScriptedProvider(text=json.dumps({"explanation": text}))


def test_checked_model_text_is_used_with_its_provenance():
    result = explain(answer(GOOD))

    assert result.explanation.text == GOOD
    assert (
        result.explanation.generated_by.kind,
        result.explanation.generated_by.name,
    ) == (
        GeneratorKind.MODEL,
        "claude-agent-sdk",
    )
    assert result.rejected_reasons == ()
    assert result.explanation.advisory is True


def test_unsafe_model_text_is_never_returned():
    result = explain(answer(GOOD + " Interaction mineure ; donner 500 mg."))

    assert result.explanation.text == template_text(WARNING)
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
    result = ExplainMedicationWarning(TemplateExplainer(), clock=lambda: FIXED_TIME)(
        WARNING
    )

    assert result.explanation.text == template_text(WARNING)
    assert (result.rejected_reasons, result.explanation.generated_by.mocked) == (
        (),
        False,
    )


def test_sends_only_the_warning_content_as_an_explanation_task():
    provider = answer(GOOD)
    explain(provider)

    [request] = provider.requests
    assert (request.task, request.output_schema) == (AiTask.EXPLANATION, OUTPUT_SCHEMA)
    assert json.loads(request.input_text) == {
        "severity": "major",
        "summary": "Risque hémorragique accru.",
        "proposed_medication": "Dolorane",
        "conflicting_medication": "Coagulix",
        "rule_source": {
            "kind": "deterministic_rule_set",
            "name": "Règles fictives de démonstration",
            "version": "1.0",
            "rule_id": "rule-coagulix-dolorane",
        },
    }


def test_the_instructions_keep_the_model_to_explaining():
    for phrase in (
        "it is correct\nas given",
        "State the warning's severity",
        "Never give a dose",
        "the decision belongs to the clinician",
    ):
        assert phrase in INSTRUCTIONS
