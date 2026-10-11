"""WarningExplainer over HTTP: AI Services' medication-warning-explanation.v1 (HC-164).

Sends one deterministic warning's content, never a patient reference or medication
history, to POST /v1/medication-warning-explanations (HC-156), and keeps the returned
Explanation only if it has the contract's shape and is advisory. AI Services checks
model text and falls back to a deterministic template itself; anything unexpected here
means no explanation, never a changed warning.
"""

from datetime import datetime

import httpx

from application.check_medication_safety import (
    ExplanationUnavailable,
    WarningExplanation,
)
from domain.medication_safety import InteractionWarning, Medication, RuleSet

EXPLANATION_PATH = "/v1/medication-warning-explanations"
GENERATOR_KINDS = {"model", "deterministic_template"}


def _medication(medication: Medication) -> dict:
    code = None
    if medication.code is not None:
        code = {"system": medication.code.system, "code": medication.code.code}
    return {"name": medication.name, "code": code}


def request_body(
    warning_id: str, warning: InteractionWarning, rules: RuleSet, requested_by: str
) -> dict:
    return {
        "requested_by": requested_by,
        "warning": {
            "warning_id": warning_id,
            "type": "drug_drug_interaction",
            "severity": warning.rule.severity.value,
            "summary": warning.rule.summary,
            "proposed_medication": _medication(warning.proposed_medication),
            "conflicting_medication": _medication(warning.conflicting.medication),
            "rule_source": {
                "kind": rules.kind.value,
                "name": rules.name,
                "version": rules.version,
                "rule_id": warning.rule.rule_id,
                "reference": warning.rule.reference,
            },
        },
    }


def explanation_from_wire(payload: object, warning_id: str) -> WarningExplanation:
    """The contract's Explanation, or ExplanationUnavailable if anything is off."""
    try:
        if (
            payload.get("warning_id") != warning_id
            or payload.get("advisory") is not True
        ):
            raise ValueError("not an advisory explanation of this warning")
        explanation = payload["explanation"]
        by = explanation["generated_by"]
        text = explanation["text"]
        checks = (
            isinstance(text, str) and text.strip(),
            explanation["advisory"] is True,
            by["kind"] in GENERATOR_KINDS,
            isinstance(by["name"], str) and by["name"],
            isinstance(by["version"], str) and by["version"],
            isinstance(by["mocked"], bool),
        )
        if not all(checks):
            raise ValueError("the explanation does not match the contract")
        generated_at = explanation["generated_at"]
        if datetime.fromisoformat(generated_at).tzinfo is None:
            raise ValueError("generated_at has no UTC offset")
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ExplanationUnavailable(f"Invalid explanation: {error}") from error
    return WarningExplanation(
        text=text,
        generator_kind=by["kind"],
        generator_name=by["name"],
        generator_version=by["version"],
        generator_mocked=by["mocked"],
        generated_at=generated_at,
    )


class AiServicesWarningExplainer:
    def __init__(
        self, base_url: str, timeout_seconds: float = 30.0, transport=None
    ) -> None:
        self._url = base_url.rstrip("/") + EXPLANATION_PATH
        self._timeout = timeout_seconds
        self._transport = transport

    def explain(
        self,
        warning_id: str,
        warning: InteractionWarning,
        rules: RuleSet,
        requested_by: str,
    ) -> WarningExplanation:
        try:
            with httpx.Client(
                timeout=self._timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = client.post(
                    self._url,
                    json=request_body(warning_id, warning, rules, requested_by),
                )
        except httpx.HTTPError as error:
            raise ExplanationUnavailable(f"Cannot reach {self._url}.") from error
        if response.status_code != 200:
            raise ExplanationUnavailable(
                f"{self._url} answered HTTP {response.status_code}."
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise ExplanationUnavailable(f"{self._url} did not answer JSON.") from error
        return explanation_from_wire(payload, warning_id)
