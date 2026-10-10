import pytest

from domain.document_review import (
    DocumentQuote,
    Dossier,
    DossierDocument,
    DossierField,
    FindingCategory,
    InvalidDossier,
    ReviewFinding,
    verified,
)

ARCHITECTURE = DossierDocument(
    "doc-c-architecture",
    "technical_architecture",
    "Architecture technique du SIH.pdf",
    "received",
    "Document fictif. Sa base de données est PostgreSQL 12, sauvegardée chaque nuit.",
)
DOSSIER = Dossier(
    fields=(
        DossierField("technical_questionnaire.database", "PostgreSQL 13"),
        DossierField("administrative_profile.security_contact", None),
    ),
    documents=(ARCHITECTURE,),
)


def finding(paths=(), evidence=None):
    return ReviewFinding(
        "proposal-1",
        FindingCategory.INCONSISTENCY,
        " Versions différentes. ",
        paths,
        evidence,
    )


def test_keeps_only_the_citations_the_dossier_supports():
    checked = verified(
        finding(
            ("technical_questionnaire.database", "technical_questionnaire.invented"),
            DocumentQuote("doc-c-architecture", "postgresql 12"),
        ),
        DOSSIER,
    )

    assert checked.field_paths == ("technical_questionnaire.database",)
    # A case-only difference is accepted; the document's own characters are kept.
    assert checked.evidence == DocumentQuote("doc-c-architecture", "PostgreSQL 12")
    assert checked.message == "Versions différentes."


@pytest.mark.parametrize(
    "paths, evidence",
    [
        (("technical_questionnaire.invented",), None),
        ((), DocumentQuote("doc-c-architecture", "PostgreSQL 14")),
        ((), DocumentQuote("doc-unknown", "PostgreSQL 12")),
    ],
)
def test_a_finding_citing_nothing_in_the_dossier_is_dropped(paths, evidence):
    assert verified(finding(paths, evidence), DOSSIER) is None


def test_a_quote_needs_document_text():
    no_text = Dossier(
        fields=DOSSIER.fields,
        documents=(
            DossierDocument("doc-c-statuts", "statutes", "Statuts.pdf", "received"),
        ),
    )

    assert (
        verified(finding((), DocumentQuote("doc-c-statuts", "Statuts")), no_text)
        is None
    )


@pytest.mark.parametrize(
    "build",
    [
        lambda: DossierField("Administrative.Profile", "x"),
        lambda: DossierField("a..b", "x"),
        lambda: DossierField("a.b", "x" * 501),
        lambda: Dossier(fields=()),
        lambda: Dossier(fields=(DossierField("a", 1), DossierField("a", 2))),
        lambda: Dossier(
            fields=(DossierField("a", 1),), documents=(ARCHITECTURE, ARCHITECTURE)
        ),
        lambda: DossierDocument("doc 1", "t", "t", "received"),
        lambda: DossierDocument("doc-1", "t", "t", "received", ""),
        lambda: ReviewFinding("f", FindingCategory.INCONSISTENCY, "x", ()),
        lambda: ReviewFinding("f", FindingCategory.INCONSISTENCY, " ", ("a",)),
    ],
)
def test_invalid_values(build):
    with pytest.raises(InvalidDossier):
        build()
