"""What an explainer proposes, before the use case checks it (HC-156, HC-157)."""

import json
from dataclasses import dataclass
from typing import Any

from domain.explanation import GeneratedBy

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["explanation"],
    "properties": {"explanation": {"type": "string"}},
}


@dataclass(frozen=True)
class ProposedExplanation:
    text: str
    generated_by: GeneratedBy
    uncertainty_notes: tuple[str, ...] = ()


class ExplanationUnavailable(Exception):
    """The explainer could not answer; the template is used instead."""


def explanation_text(raw: str) -> str:
    """The `explanation` of a model reply matching OUTPUT_SCHEMA."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ExplanationUnavailable("The model did not return valid JSON.") from error
    text = payload.get("explanation") if isinstance(payload, dict) else None
    if not isinstance(text, str):
        raise ExplanationUnavailable("The model returned no explanation text.")
    return text
