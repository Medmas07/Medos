"""MOCKED lab extractor (HC-155, AI_LAB_MODE=fixture).

Returns fixed results for the fictional demo report below, and nothing for any other
text. No model is called, and it is labelled `deterministic_fixture` and `mocked`. The
results still go through the same verification and flagging as a model's.
"""

from application.extract_lab_results import LabExtractorOutput
from domain.lab_extraction import (
    ExtractorInfo,
    ExtractorKind,
    ProposedResult,
    ReferenceRange,
)

# Hospital B's fictional pre-treatment panel for Patient A (demo-data/records/
# hospital-b.json, lab-b-2026-leila), as a lab report prints it.
DEMO_LAB_REPORT = """\
Laboratoire fictif de l'Hôpital B — Bilan avant traitement
Prélèvement : 20/05/2026 14:40
Hémoglobine : 12,6 g/dL (12,0 – 16,0)
Plaquettes : 245 G/L (150 – 400)
Créatinine : 11,4 mg/L (6,0 – 12,0)
Document fictif, aucune donnée réelle."""

INFO = ExtractorInfo(
    kind=ExtractorKind.DETERMINISTIC_FIXTURE,
    name="fixture-lab-extractor",
    version="hc-155-v1",
    mocked=True,
)

DEMO_PROPOSALS = (
    ProposedResult(
        "Hémoglobine",
        12.6,
        "g/dL",
        "Hémoglobine : 12,6 g/dL (12,0 – 16,0)",
        ReferenceRange(12.0, 16.0),
    ),
    ProposedResult(
        "Plaquettes",
        245,
        "G/L",
        "Plaquettes : 245 G/L (150 – 400)",
        ReferenceRange(150, 400),
    ),
    ProposedResult(
        "Créatinine",
        11.4,
        "mg/L",
        "Créatinine : 11,4 mg/L (6,0 – 12,0)",
        ReferenceRange(6.0, 12.0),
    ),
)


class FixtureLabExtractor:
    def extract(self, report: str) -> LabExtractorOutput:
        return LabExtractorOutput(
            proposals=DEMO_PROPOSALS if report.strip() == DEMO_LAB_REPORT else (),
            extractor=INFO,
            uncertainty_notes=(
                "Deterministic demo fixture (MOCKED): no language model was called.",
            ),
        )
