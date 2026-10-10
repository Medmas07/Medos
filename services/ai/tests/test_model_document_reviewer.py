import json

import pytest

from application.ai_provider import AiProviderErrorKind, AiTask
from application.model_document_reviewer import (
    INSTRUCTIONS,
    OUTPUT_SCHEMA,
    ModelDocumentReviewer,
)
from application.review_hospital_documents import ReviewUnavailable
from domain.document_review import DocumentQuote, FindingCategory, ReviewerKind
from tests.test_document_review_domain import DOSSIER
from tests.test_model_clinical_extractor import ScriptedProvider


def finding(
    category="inconsistency", message="Versions différentes.", paths=None, evidence=None
):
    return {
        "category": category,
        "message": message,
        "field_paths": ["technical_questionnaire.database"] if paths is None else paths,
        "evidence": evidence,
    }


def run(payload, **kwargs):
    provider = ScriptedProvider(text=json.dumps(payload), **kwargs)
    return ModelDocumentReviewer(provider, new_request_id=lambda: "req-1").review(
        DOSSIER
    ), provider


def test_sends_a_review_request_with_the_dossier_and_schema():
    _, provider = run({"findings": []})

    [request] = provider.requests
    assert (request.request_id, request.task, request.output_schema) == (
        "req-1",
        AiTask.REVIEW,
        OUTPUT_SCHEMA,
    )
    sent = json.loads(request.input_text)
    assert {
        "path": "technical_questionnaire.database",
        "value": "PostgreSQL 13",
    } in sent["fields"]
    assert sent["documents"][0]["text"].startswith("Document fictif.")


def test_the_instructions_keep_the_model_out_of_the_decision():
    for phrase in (
        "You do not decide",
        "A human reviewer decides",
        "Never invent a path",
    ):
        assert phrase in INSTRUCTIONS


def test_maps_findings_and_reports_the_answering_provider():
    output, _ = run(
        {
            "findings": [
                finding(
                    evidence={
                        "document_ref": "doc-c-architecture",
                        "quote": "PostgreSQL 12",
                    }
                ),
                finding(
                    "missing_information",
                    "Pas de contact.",
                    ["administrative_profile.security_contact"],
                ),
            ]
        }
    )

    assert [f.category for f in output.findings] == [
        FindingCategory.INCONSISTENCY,
        FindingCategory.MISSING_INFORMATION,
    ]
    assert output.findings[0].evidence == DocumentQuote(
        "doc-c-architecture", "PostgreSQL 12"
    )
    assert (output.reviewer.kind, output.reviewer.name, output.reviewer.mocked) == (
        ReviewerKind.MODEL,
        "claude-agent-sdk",
        False,
    )


def test_ignores_malformed_findings_and_counts_uncited_ones():
    output, _ = run(
        {
            "findings": [
                finding(category="approval"),  # not a review category
                finding(message=" "),
                "not an object",
                finding(paths=[], evidence=None),  # cites nothing
                finding(
                    paths=[42],
                    evidence={"document_ref": "doc-c-architecture", "quote": " "},
                ),
                finding(),
            ]
        }
    )

    assert len(output.findings) == 1
    assert output.uncited == 2


@pytest.mark.parametrize("text", ["not json", "[]", ""])
def test_unusable_model_output_is_unavailable(text):
    with pytest.raises(ReviewUnavailable):
        ModelDocumentReviewer(ScriptedProvider(text=text)).review(DOSSIER)


def test_provider_failure_is_unavailable():
    with pytest.raises(ReviewUnavailable):
        ModelDocumentReviewer(
            ScriptedProvider(error=AiProviderErrorKind.UNAVAILABLE)
        ).review(DOSSIER)
