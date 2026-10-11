"""What every advisory explanation carries (HC-156, HC-157).

An explanation only puts a deterministic result in words: a medication warning, or a
priority queue entry. It records who wrote it, a model or a deterministic template,
and is always advisory.
"""

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class GeneratorKind(Enum):
    MODEL = "model"
    DETERMINISTIC_TEMPLATE = "deterministic_template"


@dataclass(frozen=True)
class GeneratedBy:
    kind: GeneratorKind
    name: str
    version: str
    mocked: bool


@dataclass(frozen=True)
class Explanation:
    """Advisory text; never the source of the result it explains."""

    text: str
    generated_by: GeneratedBy
    generated_at: datetime
    advisory: bool = True


def plain(text: str) -> str:
    """Lower case without accents, for term matching."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
