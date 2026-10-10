# Research Service

## Purpose and status

IMPLEMENTED at initial D3 for HC-182. The service orchestrates a governed
Compute-to-Data job across explicit Governance and Hospital Node HTTP
boundaries. It does not execute researcher code, read hospital storage, or
aggregate node results.

The orchestration code and its boundary behavior are test-validated. Live
cross-process integration is **not VALIDATED** because the Governance research
authorization endpoint and Hospital-side execution agent (HC-183) are not yet
implemented. With no endpoints configured, `/health` reports `degraded` and a
submitted job fails closed with `governance_unavailable`.

## D3 behavior

`POST /v1/research-jobs`:

1. asks the Governance boundary to verify the referenced decision and exact
   organizations/scope;
2. denies without contacting a Hospital Node when Governance refuses;
3. submits one HC-180 execution request to every authorized Hospital Node;
4. retains only orchestration state and controlled node outcomes in memory.

`GET /v1/research-jobs/{job_ref}` refreshes accepted executions and exposes
queued/authorizing/dispatching/running/completed/denied/failed behavior. A
partial node failure is explicit and never silently converted into a complete
result. Per-node controlled results stay separate because aggregation belongs
to HC-184.

The runtime has no fixture mode. Test doubles exist only under `tests/` and all
runtime responses carry `mocked: false`.

## Configuration

- `RESEARCH_GOVERNANCE_URL`: Governance Node base URL.
- `RESEARCH_NODE_ENDPOINTS`: JSON object mapping organization references to
  Hospital Node base URLs, for example
  `{"org-hospital-a":"http://127.0.0.1:8101"}`.
- `RESEARCH_HTTP_TIMEOUT_SECONDS`: positive request timeout, default `5`.

Run from this directory with `uvicorn main:app --port 8400`. The service keeps
jobs in process-local memory; durable persistence, authentication, retries,
aggregation, output validation, sandboxing, and hospital-side execution remain
outside HC-182.

## Boundaries

Domain and Application use only the Python standard library. HTTP and
environment details live in outbound adapters and infrastructure. The service
does not approve its own access, connect to a hospital database or DMI, expose
row-level records, or turn research findings into clinical truth.
