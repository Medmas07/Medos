"""Plain-language explanation of a priority queue entry (HC-157).

A deterministic priority method (Priority Engine) ranked the entry from its factors:
abnormal results, interactions, late follow-up, and so on. The explanation only puts
that ranking in words for the clinician. It never sets or changes the rank or the
priority, assesses urgency, interprets the patient's condition, or tells the clinician
what to do: AI is not a triage mechanism.

The model never sees the factor ids, which may carry meaning (an id such as
"alert-hba1c" names a test): it gets each factor's position, F1, F2, ..., and must cite
every factor it explains as [F1], [F2], ..., and only those. Its text is checked here
before anyone sees it; text that fails a check is discarded and the deterministic
template below is returned instead.
"""

import re
from dataclasses import dataclass
from enum import Enum

from domain.explanation import plain

MAX_EXPLANATION_LENGTH = 800
MAX_FACTORS = 10

_REF = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
_OPAQUE_REF = re.compile(rf"^{_REF}$")
CITATION = re.compile(rf"\s*\[({_REF})\]")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")

# Urgency or triage the method did not assess, matched without accents.
_URGENCY = re.compile(
    r"\burgen\w*|\bcritique\w*|\bcritical\w*|\bemergenc\w*|\bimmediat\w*|\bvital\w*|"
    r"\blife[- ]threatening\b|\bsans (?:delai|attendre)\b|\bwithout delay\b"
)
# A reading of the patient's condition that no factor states.
_INTERPRETATION = re.compile(
    r"\bdiagnos\w*|\bsugger\w*|\bsuggest\w*|\bevoqu\w*|\bprobabl\w*|\blikely\b|"
    r"\bcompatible avec\b|\bconsistent with\b|\bmal (?:controle|equilibre)\w*|"
    r"\bpoorly controlled\b|\bdesequilibr\w*|\bdeteriorat\w*|\baggrav\w*"
)
# A directive to the clinician: the entry carries none.
_DIRECTIVE = re.compile(
    r"\brecommand\w*|\brecommend\w*|\bconseill\w*|\bshould\b|\bmust\b|"
    r"\bdevr(?:ait|aient|iez|ez|a)\b|\bil faut\b|\b(?:voir|recevoir|examiner) "
    r"[^.]{0,30}en premier\b|\bsee [^.]{0,30}first\b|"
    r"\bconvoqu\w*|\bappel(?:er|ez)\b|\bcall\b|\bhospitalis\w*|\bprescri\w*|"
    r"\btrait(?:er|ez)\b|\bprendre en charge\b"
)


class InvalidQueueEntry(ValueError):
    pass


class Level(Enum):
    """A priority, or a factor's severity, as the priority method states it."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FactorType(Enum):
    # The patient events of the product vision (section 19), plus patient context.
    ABNORMAL_LAB = "abnormal_lab"
    POSSIBLE_DRUG_INTERACTION = "possible_drug_interaction"
    MISSED_FOLLOW_UP = "missed_follow_up"
    PATIENT_DETERIORATION = "patient_deterioration"
    NEW_EXTERNAL_CONSULTATION = "new_external_consultation"
    UNRESOLVED_ALERT = "unresolved_alert"
    PATIENT_CONTEXT = "patient_context"


class MethodKind(Enum):
    # Only deterministic methods rank the queue. A model is not one of them.
    DETERMINISTIC_RULE_SET = "deterministic_rule_set"
    DETERMINISTIC_MOCK = "deterministic_mock"


# How each priority must be named: "priorité haute", "high priority", ... matched
# without accents. A level word alone is not enough: "sévérité haute" is a factor's.
PRIORITY_TERMS: dict[Level, re.Pattern[str]] = {
    Level.HIGH: re.compile(
        r"\bpriorite\s*:?\s*(?:haute|elevee|forte)\b|\b(?:haute|forte) priorite\b|"
        r"\bhigh[- ]priority\b|\bpriority\s*(?::|is|of)?\s*high\b"
    ),
    Level.MEDIUM: re.compile(
        r"\bpriorite\s*:?\s*(?:moyenne|intermediaire)\b|\bmoyenne priorite\b|"
        r"\bmedium[- ]priority\b|\bpriority\s*(?::|is|of)?\s*medium\b"
    ),
    Level.LOW: re.compile(
        r"\bpriorite\s*:?\s*(?:basse|faible)\b|\b(?:basse|faible) priorite\b|"
        r"\blow[- ]priority\b|\bpriority\s*(?::|is|of)?\s*low\b"
    ),
}
LEVEL_LABELS_FR = {Level.HIGH: "haute", Level.MEDIUM: "moyenne", Level.LOW: "basse"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidQueueEntry(message)


def _text(value: str | None, field: str, limit: int) -> None:
    _require(
        value is not None and 0 < len(value.strip()) <= limit,
        f"{field} must be 1-{limit} characters",
    )


@dataclass(frozen=True)
class PriorityMethod:
    kind: MethodKind
    name: str
    version: str
    description: str | None = None

    @property
    def mocked(self) -> bool:
        return self.kind is MethodKind.DETERMINISTIC_MOCK


@dataclass(frozen=True)
class PriorityFactor:
    factor_id: str
    type: FactorType
    label: str
    severity: Level
    weight: float | None = None


@dataclass(frozen=True)
class QueueEntry:
    """One ranked entry of a clinician's queue, as the priority method produced it."""

    entry_id: str
    rank: int
    priority: Level
    factors: tuple[PriorityFactor, ...]
    method: PriorityMethod
    score: float | None = None

    def __post_init__(self) -> None:
        _text(self.entry_id, "entry_id", 128)
        _require(self.rank >= 1, "rank must be 1 or more")
        _require(
            1 <= len(self.factors) <= MAX_FACTORS,
            f"an entry has 1-{MAX_FACTORS} factors",
        )
        ids = [f.factor_id for f in self.factors]
        _require(len(set(ids)) == len(ids), "factor ids must be unique")
        for factor in self.factors:
            _require(
                bool(_OPAQUE_REF.match(factor.factor_id)),
                "factor_id must be an opaque reference",
            )
            _text(factor.label, "factor label", 200)
        _text(self.method.name, "method.name", 200)
        _text(self.method.version, "method.version", 100)


def citation(index: int) -> str:
    """How the model refers to the factor at `index`; its id is not shown to it."""
    return f"F{index + 1}"


def displayed_text(text: str) -> str:
    """The text without its [F1] citations, as the clinician reads it."""
    return re.sub(r" {2,}", " ", CITATION.sub("", text)).strip()


def _numbers(text: str) -> set[float]:
    return {float(n.replace(",", ".")) for n in _NUMBER.findall(text)}


def _new_terms(pattern: re.Pattern[str], folded: str, entry_text: str) -> list[str]:
    """Matches of `pattern` the entry's own words do not contain."""
    return [m for m in pattern.findall(folded) if m not in entry_text]


def guardrail_problems(text: str, entry: QueueEntry) -> list[str]:
    """Why a proposed explanation cannot be shown; empty when it can."""
    shown = displayed_text(text)
    if not shown:
        return ["the explanation is empty"]
    problems = []
    folded = plain(shown)
    entry_words = " ".join(
        [f.label for f in entry.factors]
        + [entry.method.name, entry.method.description or ""]
    )
    entry_text = plain(entry_words)
    if len(shown) > MAX_EXPLANATION_LENGTH:
        problems.append(
            f"the explanation is longer than {MAX_EXPLANATION_LENGTH} characters"
        )
    cited = set(CITATION.findall(text))
    refs = {citation(i): f.factor_id for i, f in enumerate(entry.factors)}
    for ref, factor_id in refs.items():
        if ref not in cited:
            problems.append(f"the explanation does not cite the factor {factor_id}")
    for ref in sorted(cited - refs.keys()):
        problems.append(f"the explanation cites [{ref}], which is not in the entry")
    if not PRIORITY_TERMS[entry.priority].search(folded):
        problems.append(
            f"the explanation does not state the priority {entry.priority.value}"
        )
    for level, pattern in PRIORITY_TERMS.items():
        if level is not entry.priority and pattern.search(folded):
            problems.append(
                f"the explanation names a priority other than {entry.priority.value}"
            )
            break
    given = [entry.score] + [f.weight for f in entry.factors]
    allowed = (
        _numbers(entry_words)
        | _numbers(entry.method.version)
        | {float(entry.rank), float(len(entry.factors))}
        | {float(n) for n in given if n is not None}
    )
    invented = sorted(_numbers(shown) - allowed)
    if invented:
        problems.append(
            "the explanation contains a number that is not in the entry: "
            + ", ".join(f"{n:g}" for n in invented)
        )
    if _new_terms(_URGENCY, folded, entry_text):
        problems.append("the explanation claims an urgency the method did not assess")
    if _new_terms(_INTERPRETATION, folded, entry_text):
        problems.append("the explanation interprets the patient's condition")
    if _new_terms(_DIRECTIVE, folded, entry_text):
        problems.append("the explanation tells the clinician what to do")
    return problems


def _number(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def template_text(entry: QueueEntry) -> str:
    """The deterministic explanation: the entry's own content, in fixed sentences."""
    method = entry.method
    score = f", score {_number(entry.score)}" if entry.score is not None else ""
    simulated = ", simulée" if method.mocked else ""
    factors = " ; ".join(
        f"{f.label.strip().rstrip('.')} (sévérité {LEVEL_LABELS_FR[f.severity]})"
        for f in entry.factors
    )
    return (
        f"Priorité {LEVEL_LABELS_FR[entry.priority]}, rang {entry.rank} dans la file"
        f"{score}, selon la méthode « {method.name.strip()} » (version "
        f"{method.version.strip()}{simulated}), à partir de : {factors}. Ce classement "
        f"n'est pas un triage clinique. La décision appartient au clinicien."
    )
