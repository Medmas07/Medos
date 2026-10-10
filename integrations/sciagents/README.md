# SciAgents Integration

## Purpose and status

SciAgents exists externally. This repository owns only its integration. The repository-side communication contract is IMPLEMENTED as [`scientific-investigation.v1.yaml`](../../contracts/api/sciagents/scientific-investigation.v1.yaml) (HC-170), and the server-side HTTP client adapter is IMPLEMENTED at D2 under [`src/sciagents_adapter/`](src/sciagents_adapter/) (HC-171). It is a Python library boundary per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md), not a separate speculative service. The Research Portal connection remains PLANNED (HC-172).

## Responsibilities and owned concepts

Client adapter, authentication boundary, request/response mapping, timeouts, error mapping, experiment provenance, and Research Portal integration.

## Communication boundaries

The Research Service/Portal communicates through provider-neutral contracts; SciAgents-specific details remain in this adapter boundary.

## Non-responsibilities

This repository does not own or reimplement SciAgents, and SciAgents output does not automatically become clinical truth.

## Contracts

[`scientific-investigation.v1.yaml`](../../contracts/api/sciagents/scientific-investigation.v1.yaml) is the provider-neutral contract the Research Service and Research Portal use. It does **not** expose SciAgents' own API; the adapter maps between the two.

- `POST /v1/investigations` submits a display question plus exactly two non-identifying biomedical concepts and returns `202` with a `queued` investigation. `GET /v1/investigations/{id}` returns its `status` (`queued`, `running`, `completed`, `failed`), `progress` for HC-173, and either `result` or `error`.
- Results hold hypotheses, evidence, contradictions, and citations, linked by id. Every referenced id must exist in the same result; the schema cannot express this, so the adapter must guarantee it, and the contract tests check the examples.
- Results are research leads only (`clinical_use: not_for_clinical_decisions`) and carry provenance, including `mocked`.
- Requests may carry only the display question, exactly two biomedical concept labels, and opaque workflow references. The schema rejects controlled-result content, patient references, and any other field. HC-171 maps only the two concept labels to SciAgents' `keywords`; it does not send the display question.
- The examples reuse the canonical HC-005 fictional workflow references `proj-001` and `usr-aymen`; their scientific content is explicitly fictional and demonstrates only the adapter mapping.
- The Research Portal's SciAgents panel (HC-102) displays a MOCKED fixture investigation. It does not call this adapter or SciAgents yet (HC-172).

## Observed upstream API boundary for HC-171

The external code inspected for HC-171 exposes an open FastAPI API. `POST /hypotheses` accepts exactly two `keywords` plus execution controls and returns either an inline `200` summary or an asynchronous `202 {run_id, status}`. `POST /hypotheses/stream` emits SSE events (`start`, `step`, `node_output`, `paused`, `done`, `error`), and `GET /hypotheses/{run_id}` returns the persisted run state.

There is no upstream user authentication, workspace boundary, free-form question field, language field, or controlled-result input. Runs are global and the upstream version reports `0.0.0`. HC-171 therefore keeps SciAgents server-side, normalizes inline and queued execution, maps errors and polling progress, applies timeouts, and preserves provenance without claiming production authentication. Confidence stays `null`; Critic prose is not turned into a contradiction automatically.

The adapter keeps the Hackcure investigation UUID to upstream `run_id` correlation in process memory. A restart loses that correlation, and concurrent replicas do not share it. It does not expose an HTTP route, consume SSE yet, authenticate SciAgents, retry calls, or provide durable storage; those are explicit D2 limits. Tests use `httpx.MockTransport` only and are not delivered as a mock integration. A real configured SciAgents endpoint is required for live use.

## Development

```powershell
$env:PYTHONPATH = "src"
python -m pytest
python -m ruff check .
```
