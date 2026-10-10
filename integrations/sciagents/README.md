# SciAgents Integration

## Purpose and status

SciAgents exists externally. This repository owns only its integration. The repository-side communication contract is IMPLEMENTED as [`scientific-investigation.v1.yaml`](../../contracts/api/sciagents/scientific-investigation.v1.yaml) (HC-170); the client adapter is PLANNED (HC-171), and no code exists. The client adapter is Python per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md); HC-171 decides whether it runs inside the Research Service or as its own process.

## Responsibilities and owned concepts

Client adapter, authentication boundary, request/response mapping, timeouts, error mapping, experiment provenance, and Research Portal integration.

## Communication boundaries

The Research Service/Portal communicates through provider-neutral contracts; SciAgents-specific details remain in this adapter boundary.

## Non-responsibilities

This repository does not own or reimplement SciAgents, and SciAgents output does not automatically become clinical truth.

## Contracts

[`scientific-investigation.v1.yaml`](../../contracts/api/sciagents/scientific-investigation.v1.yaml) is the provider-neutral contract the Research Service and Research Portal use. It does **not** describe SciAgents' own API, which is OPEN; the adapter maps between the two.

- `POST /v1/investigations` submits a question and returns `202` with a `queued` investigation. `GET /v1/investigations/{id}` returns its `status` (`queued`, `running`, `completed`, `failed`), `progress` for HC-173, and either `result` or `error`.
- Results hold hypotheses, evidence, contradictions, and citations, linked by id. Every referenced id must exist in the same result; the schema cannot express this, so the adapter must guarantee it, and the contract tests check the examples.
- Results are research leads only (`clinical_use: not_for_clinical_decisions`) and carry provenance, including `mocked`.
- Requests may carry only the question, opaque references, and summaries of controlled results that passed Compute-to-Data output validation. The schema rejects any other field, so raw clinical data cannot be sent to SciAgents through this contract.
- The completed example matches the HC-005 fixture `inv-001` in [`demo-data/research.json`](../../demo-data/research.json), including its hypothesis links, citation kinds, and controlled-result context; `demo-data/check_fixtures.py` checks that its references resolve and that it cites or sends only released controlled results.
- The Research Portal's SciAgents panel (HC-102) displays that fixture in the contract's shape. It is MOCKED: the portal does not call this contract or SciAgents yet (HC-172).

SciAgents authentication, timeouts, and the real endpoint mapping belong to HC-171.
