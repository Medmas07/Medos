"""Translate the HC-170 investigation boundary to the external SciAgents API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

ADAPTER_NAME = "hackcure-sciagents-adapter"
ADAPTER_VERSION = "0.1.0"


class SciAgentsAdapterError(RuntimeError):
    """Structured failure raised when no investigation can be created."""

    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class _InvestigationRecord:
    investigation_id: str
    project_ref: str
    requested_by: str
    question: str
    concepts: tuple[dict[str, str], dict[str, str]]
    upstream_run_id: str
    created_at: str


class SciAgentsClient:
    """Synchronous HC-171 client with process-local request correlation.

    The client is server-side only. It deliberately sends just two concept labels to
    SciAgents and keeps Hackcure workflow metadata inside this process.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        http_client: httpx.Client | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("SciAgents base URL is required")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._records: dict[str, _InvestigationRecord] = {}
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds
        )

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> SciAgentsClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def submit(self, request: dict[str, Any]) -> dict[str, Any]:
        """Submit exactly two concepts and return the normalized queued state."""
        project_ref = self._required_string(request, "project_ref")
        requested_by = self._required_string(request, "requested_by")
        question = self._required_string(request, "question")
        concepts = self._concepts(request)
        try:
            response = self._http.post(
                "/hypotheses",
                json={
                    "keywords": [concept["label"] for concept in concepts],
                    "mode": "sequential",
                    "human_review": False,
                },
            )
        except httpx.TimeoutException as error:
            raise SciAgentsAdapterError(
                "timeout", "SciAgents did not answer in time.", retryable=True
            ) from error
        except httpx.RequestError as error:
            raise SciAgentsAdapterError(
                "upstream_unavailable", "SciAgents is unavailable.", retryable=True
            ) from error

        if response.status_code == 422:
            raise SciAgentsAdapterError(
                "rejected_by_upstream",
                "SciAgents rejected the concept pair.",
                retryable=False,
            )
        if response.status_code >= 500:
            raise SciAgentsAdapterError(
                "upstream_error", "SciAgents failed to create the run.", retryable=True
            )
        if response.status_code not in {200, 202}:
            raise SciAgentsAdapterError(
                "upstream_error",
                f"SciAgents returned unexpected status {response.status_code}.",
                retryable=False,
            )

        document = self._json_object(response)
        run_id = document.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise SciAgentsAdapterError(
                "upstream_error", "SciAgents returned no run identifier.", retryable=False
            )

        now = self._now()
        record = _InvestigationRecord(
            investigation_id=self._id_factory(),
            project_ref=project_ref,
            requested_by=requested_by,
            question=question,
            concepts=concepts,
            upstream_run_id=run_id,
            created_at=now,
        )
        self._records[record.investigation_id] = record
        return self._investigation(record, status="queued", updated_at=now)

    def get(self, investigation_id: str) -> dict[str, Any]:
        """Poll SciAgents and normalize queued, running, completed, empty, and failed states."""
        try:
            record = self._records[investigation_id]
        except KeyError as error:
            raise KeyError("investigation_not_found") from error

        try:
            response = self._http.get(f"/hypotheses/{record.upstream_run_id}")
        except httpx.TimeoutException:
            return self._failed(record, "timeout", "SciAgents did not answer in time.", True)
        except httpx.RequestError:
            return self._failed(record, "upstream_unavailable", "SciAgents is unavailable.", True)

        if response.status_code == 404:
            return self._investigation(record, status="queued", updated_at=self._now())
        if response.status_code >= 500:
            return self._failed(
                record, "upstream_error", "SciAgents failed while reading the run.", True
            )
        if response.status_code != 200:
            return self._failed(
                record,
                "upstream_error",
                f"SciAgents returned unexpected status {response.status_code}.",
                False,
            )

        try:
            state = self._json_object(response)
        except SciAgentsAdapterError as error:
            return self._failed(record, error.code, str(error), error.retryable)
        if state.get("error"):
            return self._failed(
                record, "upstream_error", "SciAgents reported a run failure.", False
            )
        if state.get("awaiting_human") is True:
            return self._failed(
                record,
                "upstream_error",
                "SciAgents entered an unsupported human-review state.",
                False,
            )
        if state.get("evaluation") is not None or state.get("stop_reason") is not None:
            return self._completed(record, state)
        return self._running(record, state)

    @staticmethod
    def _required_string(document: dict[str, Any], key: str) -> str:
        value = document.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{key} is required")
        return value

    @classmethod
    def _concepts(cls, request: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
        raw = request.get("concepts")
        if not isinstance(raw, list) or len(raw) != 2:
            raise ValueError("exactly two concepts are required")
        concepts: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict) or set(item) != {"label"}:
                raise ValueError("each concept must contain only label")
            label = cls._required_string(item, "label")
            concepts.append({"label": label})
        return concepts[0], concepts[1]

    @staticmethod
    def _json_object(response: httpx.Response) -> dict[str, Any]:
        try:
            document = response.json()
        except ValueError as error:
            raise SciAgentsAdapterError(
                "upstream_error", "SciAgents returned invalid JSON.", retryable=False
            ) from error
        if not isinstance(document, dict):
            raise SciAgentsAdapterError(
                "upstream_error", "SciAgents returned an invalid document.", retryable=False
            )
        return document

    def _running(self, record: _InvestigationRecord, state: dict[str, Any]) -> dict[str, Any]:
        history = state.get("history")
        node = None
        if isinstance(history, list) and history and isinstance(history[-1], dict):
            node = history[-1].get("node")
        progress = {
            "stage_label": self._stage_label(node),
            "percent": None,
            "updated_at": self._now(),
        }
        return self._investigation(
            record, status="running", updated_at=progress["updated_at"], progress=progress
        )

    def _completed(self, record: _InvestigationRecord, state: dict[str, Any]) -> dict[str, Any]:
        now = self._now()
        result = self._result(record, state)
        progress = {"stage_label": "Completed", "percent": 100, "updated_at": now}
        return self._investigation(
            record,
            status="completed",
            updated_at=now,
            progress=progress,
            result=result,
        )

    def _result(self, record: _InvestigationRecord, state: dict[str, Any]) -> dict[str, Any]:
        proposal = state.get("expanded") or state.get("proposal")
        evaluation = state.get("evaluation")
        if not isinstance(proposal, dict) or (
            isinstance(evaluation, dict) and evaluation.get("passed_quality_gate") is False
        ):
            return {
                "outcome": "empty",
                "hypotheses": [],
                "evidence": [],
                "contradictions": [],
                "citations": [],
            }

        grounding = state.get("grounding")
        raw_citations = grounding.get("citations", []) if isinstance(grounding, dict) else []
        evidence: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        evidence_ids: list[str] = []
        for index, raw in enumerate(raw_citations, start=1):
            if not isinstance(raw, dict) or raw.get("resolved") is not True:
                continue
            citation_id = f"{record.investigation_id}-c{index}"
            evidence_id = f"{record.investigation_id}-e{index}"
            doc_id = str(raw.get("doc_id") or "SciAgents source")
            citations.append(
                {
                    "citation_id": citation_id,
                    "kind": "other",
                    "title": doc_id,
                    "source": "SciAgents grounding",
                    "identifier": doc_id,
                    "url": None,
                }
            )
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "summary": str(raw.get("evidence_span") or "Grounded upstream evidence."),
                    "citation_ids": [citation_id],
                }
            )
            evidence_ids.append(evidence_id)

        statement = proposal.get("hypothesis")
        if not isinstance(statement, str) or not statement:
            return {
                "outcome": "empty",
                "hypotheses": [],
                "evidence": [],
                "contradictions": [],
                "citations": [],
            }
        return {
            "outcome": "findings",
            "hypotheses": [
                {
                    "hypothesis_id": f"{record.investigation_id}-h1",
                    "statement": statement,
                    "confidence": None,
                    "evidence_ids": evidence_ids,
                    "contradiction_ids": [],
                }
            ],
            "evidence": evidence,
            "contradictions": [],
            "citations": citations,
        }

    def _failed(
        self,
        record: _InvestigationRecord,
        code: str,
        message: str,
        retryable: bool,
    ) -> dict[str, Any]:
        return self._investigation(
            record,
            status="failed",
            updated_at=self._now(),
            error={"code": code, "message": message, "retryable": retryable},
        )

    @staticmethod
    def _stage_label(node: object) -> str:
        labels = {
            "ontologist": "Ontology analysis",
            "proposer": "Hypothesis proposal",
            "expander": "Hypothesis expansion",
            "revise": "Hypothesis revision",
            "critic": "Scientific critique",
            "grounding": "Evidence grounding",
            "novelty": "Novelty assessment",
            "evaluation": "Quality evaluation",
        }
        return labels.get(str(node), "SciAgents execution")

    def _investigation(
        self,
        record: _InvestigationRecord,
        *,
        status: str,
        updated_at: str,
        progress: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "investigation_id": record.investigation_id,
            "contract_version": "1.1",
            "project_ref": record.project_ref,
            "requested_by": record.requested_by,
            "question": record.question,
            "concepts": list(record.concepts),
            "status": status,
            "progress": progress,
            "created_at": record.created_at,
            "updated_at": updated_at,
            "clinical_use": "not_for_clinical_decisions",
            "notice": "Research leads from an external system. Not for clinical decisions.",
            "result": result,
            "error": error,
            "provenance": {
                "provider": {"name": "SciAgents", "version": None},
                "adapter": {"name": ADAPTER_NAME, "version": ADAPTER_VERSION},
                "mocked": False,
                "upstream_request_ref": record.upstream_run_id,
            },
        }

    def _now(self) -> str:
        return self._clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
