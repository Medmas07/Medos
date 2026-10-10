# Research Service

## Purpose and status

IMPLEMENTED at initial D3 for HC-182/HC-184 and D4 for HC-185. The service
orchestrates a governed Compute-to-Data job across explicit Governance and
Hospital Node HTTP boundaries, validates controlled outputs before release,
and aggregates only outputs that pass. It does not execute researcher code or
read hospital storage.

The orchestration code and its boundary behavior are test-validated. The
Governance Node serves the research authorization endpoint (HC-133). Run locally with the Governance Node (HC-133) and Hospital Nodes A and B, a job under a decision whose scope the HC-183 aggregate can run (`hba1c`, encounter dates) completes on both nodes with output validation passed; the fictional cohorts are below the minimum cell size, so the aggregate is suppressed. Jobs outside the decision (a variable, organization, project, requester, or population it does not cover) are denied by Governance before any node is asked. Under `dec-rar-001` (ages 40–79), no job can complete: the HC-183 aggregate refuses age bounds, and Governance refuses a job without them as wider than approved. Live
integration is **not VALIDATED** beyond that local run.
With no endpoints configured, `/health` reports `degraded` and a submitted job
fails with `governance_unavailable`.

## D3 orchestration and aggregation

`POST /v1/research-jobs`:

1. asks the Governance boundary to verify the referenced decision and exact
   organizations/scope;
2. denies without contacting a Hospital Node when Governance refuses;
3. submits one HC-180 execution request to every authorized Hospital Node;
4. retains only orchestration state and controlled node outcomes in memory.

`GET /v1/research-jobs/{job_ref}` refreshes accepted executions and exposes
queued/authorizing/dispatching/running/completed/denied/failed behavior. A node
failure is explicit and makes aggregation unavailable.

When every node completes, the HC-184 bounded aggregator validates each result's
shape, disclosure threshold, algorithm hash, authorization reference, and source
organization before using it. It combines only the installed HC-183
`participant_count` and `hba1c_above_7_pct` cells, using participant counts as
weights. Empty results contribute no rows. Suppressed cells are never inferred:
they produce `suppressed` when no node released a result, or `partial` with an
explicit excluded-organization list when other nodes released results. Invalid
output fails closed, is removed from the response, and produces
`invalid_controlled_result`. Aggregation provenance names organizations, never
patients.

## D4 output-validation gate

HC-185 validates every completed Hospital Node output before the service exposes
or aggregates it. The bounded gate checks:

- the exact controlled-result and metadata shape, rejecting unexpected fields;
- the output policy and minimum-cell threshold;
- the algorithm, authorization, organization, and node provenance binding;
- timezone-aware execution/review timestamps and their order;
- the installed aggregate's exact columns, single-row bound, count, and numeric
  percentage range.

Each node outcome exposes `output_validation` as `pending`, `passed`, `rejected`,
or `not_applicable`, with the checks that passed. A rejected output is removed,
the job fails with `output_rejected`, and aggregation becomes `not_available`.
The gate does not repair output, infer suppressed cells, inspect Hospital Node
storage, or claim generic de-identification. It is deterministic validation for
the one installed HC-183 aggregate, not production disclosure-control tooling.

The runtime has no fixture mode. Test doubles exist only under `tests/`.
Service responses carry `mocked: false`; each node outcome and aggregation also
carry whether their source Hospital Node identified its data as mocked.

## Configuration

- `RESEARCH_GOVERNANCE_URL`: Governance Node base URL.
- `RESEARCH_NODE_ENDPOINTS`: JSON object mapping organization references to
  Hospital Node base URLs, for example
  `{"org-hospital-a":"http://127.0.0.1:8101"}`.
- `RESEARCH_HTTP_TIMEOUT_SECONDS`: positive request timeout, default `5`.

Run from this directory with `uvicorn main:app --port 8400`. The service keeps
jobs in process-local memory; durable persistence, authentication, retries,
general-purpose aggregation, generic de-identification, sandboxing, and
production disclosure technology remain outside HC-182/HC-184/HC-185.

## Boundaries

Domain and Application use only the Python standard library. HTTP and
environment details live in outbound adapters and infrastructure. The service
does not approve its own access, connect to a hospital database or DMI, expose
row-level records, or turn research findings into clinical truth.
