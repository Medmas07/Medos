"""Plain-language explanation of a deterministic medication warning (HC-156).

The explanation layer the medication safety contract reserves for AI Services
(medication-safety-check.v1.yaml, `Warning.explanation`). The warning exists because a
deterministic rule set or a validated source produced it; the explanation only puts it
in words for the clinician. It never changes the severity, adds an interaction, gives a
dose, or decides: AI is never the safety source.

Model text is checked here before anyone sees it. Text that fails a check is discarded
and the deterministic template below is returned instead.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

MAX_EXPLANATION_LENGTH = 800

# A dose or administration quantity: a number followed by a unit or a frequency.
_DOSE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:mg|µg|mcg|g|ml|mL|ui|UI|iu|IU|unit(?:é|e)s?|comprimés?|gélules?|"
    r"gouttes?|tablets?|capsules?|drops?)\b"
    r"|\d+\s*(?:fois|x)\s*(?:par|/)\s*(?:jour|j|day)\b",
    re.IGNORECASE,
)


# A directive to the clinician, in French or English, matched without accents. The
# warning carries no recommendation, so any directive is the model's own. "Prescrire"
# is not listed: faithful text says the decision to prescribe is the clinician's.
_DIRECTIVE = re.compile(
    r"\brecommand|\bconseill|\bevit(?:er|ez)\b|\bne (?:pas|jamais) (?:associer|"
    r"combiner|donner|administrer|utiliser)\b|\barret(?:er|ez)\b|\binterromp|"
    r"\bremplac(?:er|ez)\b|\bsubstitu|\brecommend|\bavoid|\bshould\b|\bdiscontinu|"
    r"\bswitch(?:ing)?\b|\bstop(?:ping)?\b"
)


class InvalidWarning(ValueError):
    pass


class Severity(Enum):
    CONTRAINDICATED = "contraindicated"
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"


class SafetySourceKind(Enum):
    # The only safety sources the medication contract allows. An LLM is not one.
    DETERMINISTIC_RULE_SET = "deterministic_rule_set"
    VALIDATED_SOURCE = "validated_source"


class GeneratorKind(Enum):
    MODEL = "model"
    DETERMINISTIC_TEMPLATE = "deterministic_template"


# Whole words naming each severity, in French and English, matched without accents.
# Text naming another severity than the warning's contradicts the rule source. Whole
# words, so "majoration du risque" does not read as "major".
SEVERITY_TERMS: dict[Severity, re.Pattern[str]] = {
    Severity.CONTRAINDICATED: re.compile(
        r"\bcontre[- ]indique(?:e|s|es)?\b|\bcontraindicat(?:ed|ion)s?\b"
    ),
    Severity.MAJOR: re.compile(r"\bmajeure?s?\b|\bmajor\b|\bgraves?\b|\bsevere\b"),
    Severity.MODERATE: re.compile(r"\bmoderee?s?\b|\bmoderate\b"),
    Severity.MINOR: re.compile(r"\bmineure?s?\b|\bminor\b"),
}
SEVERITY_LABELS_FR = {
    Severity.CONTRAINDICATED: "contre-indiquée",
    Severity.MAJOR: "majeure",
    Severity.MODERATE: "modérée",
    Severity.MINOR: "mineure",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidWarning(message)


def _plain(text: str) -> str:
    """Lower case without accents, for term matching."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


@dataclass(frozen=True)
class RuleSource:
    kind: SafetySourceKind
    name: str
    version: str
    rule_id: str
    reference: str | None = None


@dataclass(frozen=True)
class MedicationWarning:
    """The warning to explain, as the medication safety contract carries it."""

    warning_id: str
    severity: Severity
    summary: str
    proposed_medication: str
    conflicting_medication: str
    rule_source: RuleSource

    def __post_init__(self) -> None:
        for field in (
            "warning_id",
            "summary",
            "proposed_medication",
            "conflicting_medication",
        ):
            value = getattr(self, field)
            _require(0 < len(value.strip()) <= 500, f"{field} must be 1-500 characters")
        for field in ("name", "version", "rule_id"):
            _require(
                bool(getattr(self.rule_source, field).strip()),
                f"rule_source.{field} is required",
            )


@dataclass(frozen=True)
class GeneratedBy:
    kind: GeneratorKind
    name: str
    version: str
    mocked: bool


@dataclass(frozen=True)
class Explanation:
    """The medication contract's `Explanation`: advisory, never the safety source."""

    text: str
    generated_by: GeneratedBy
    generated_at: datetime
    advisory: bool = True


def guardrail_problems(text: str, warning: MedicationWarning) -> list[str]:
    """Why a proposed explanation cannot be shown; empty when it can."""
    problems = []
    plain = _plain(text)
    if not text.strip():
        return ["the explanation is empty"]
    if len(text) > MAX_EXPLANATION_LENGTH:
        problems.append(
            f"the explanation is longer than {MAX_EXPLANATION_LENGTH} characters"
        )
    for medication in (warning.proposed_medication, warning.conflicting_medication):
        if _plain(medication.strip()) not in plain:
            problems.append(f"the explanation does not name {medication.strip()}")
    if not SEVERITY_TERMS[warning.severity].search(plain):
        problems.append(
            f"the explanation does not state the severity {warning.severity.value}"
        )
    for severity, pattern in SEVERITY_TERMS.items():
        if severity is not warning.severity and pattern.search(plain):
            problems.append(
                f"the explanation names a severity other than {warning.severity.value}"
            )
            break
    if _DOSE.search(text):
        problems.append("the explanation contains a dose or an administration quantity")
    if _DIRECTIVE.search(plain):
        problems.append("the explanation tells the clinician what to do")
    return problems


def template_text(warning: MedicationWarning) -> str:
    """The deterministic explanation: the warning's own content, in a fixed sentence."""
    summary = warning.summary.strip()
    if not summary.endswith((".", "!", "?")):
        summary += "."
    return (
        f"Interaction {SEVERITY_LABELS_FR[warning.severity]} entre "
        f"{warning.proposed_medication.strip()} et {warning.conflicting_medication.strip()} "
        f"selon {warning.rule_source.name} (règle {warning.rule_source.rule_id}) : "
        f"{summary} La décision appartient au clinicien."
    )
