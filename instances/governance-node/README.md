# Governance Node

## Purpose and status

CONFIRMED Governance / Ethics Authority boundary. Its stack (Python + FastAPI, one process) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED at D2 (HC-130): a FastAPI app with Clean/Hexagonal layers, pinned dependencies, tests, and a liveness `GET /health`. **It serves no governance API yet:** hospital approval (HC-131), synchronization requests (HC-132), research requests (HC-133), audit (HC-134), policy (HC-135), and consent evaluation (HC-136) are PLANNED, so the Node records and authorizes nothing. There is no persistence, no authentication, and no ledger adapter. It is not deployed.

## Running locally

From this directory (POSIX shell; on Windows activate with `.venv\Scripts\activate`).

| Purpose | Command |
|---|---|
| Create environment | `python3 -m venv .venv && . .venv/bin/activate` |
| Install (dev) | `pip install -r requirements-dev.txt` |
| Server on port 8200 | `python main.py` |
| Dev server with reload | `fastapi dev main.py --port 8200` |
| Tests | `pytest` |
| Lint / format check | `ruff check . && ruff format --check .` |
| Production-mode server (preview) | `fastapi run main.py --port 8200` |

`python main.py` listens on `127.0.0.1:8200`, the ADR-0003 port that the Federation Service already calls (`FEDERATION_GOVERNANCE_URL`). `fastapi dev` and `fastapi run` need `--port 8200`.

## Runtime skeleton (HC-130)

IMPLEMENTED at D2. One process, so there is no per-instance configuration file. The identity is the fictional Governance / Ethics Authority of the demo dataset, set in `main.py`: node `node-governance`, organization `org-governance` ([`demo-data/organizations.json`](../../demo-data/organizations.json)). It is not authenticated.

```text
main.py                         # composition root: identity, FastAPI app, routers
domain/                         # NodeIdentity (opaque refs), NodeStatus and its notice
application/get_node_status.py  # use case; declares capabilities as their APIs land
adapters/inbound/http/health.py # GET /health
tests/                          # use case, HTTP, and layer-boundary tests
```

`GET /health` is a liveness check only:

```json
{
  "status": "ok",
  "node": "governance-node",
  "version": "0.1.0",
  "node_ref": "node-governance",
  "organization_ref": "org-governance",
  "capabilities": [],
  "notice": "Governance Node runtime skeleton (HC-130). ... Liveness only; not a production health check."
}
```

`capabilities` stays empty until a governance API is served. Every other route answers `404`. In particular, the Federation Service's synchronization authorization check (`POST /v1/synchronization-authorizations/{decision_ref}/checks`) gets `404`, which it treats as unavailable, so it still refuses those queries with `503`. A test checks that only `/health` is served, so each new route must come with its ticket.

`domain/` and `application/` use the standard library only; FastAPI and Pydantic stay in `adapters/` and `main.py`, as the layer-boundary test checks.

## Responsibilities and owned concepts

- Hospital approval and registry. The Federation Service's node registry ([`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml), HC-142) is only a routing directory: each registration cites a Governance approval decision, which the Federation Service cannot verify until this Node exposes an approval API (HC-131).
- Synchronization and research authorization. The Federation Service already calls [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) on this Node before every synchronization-decision query (HC-144); until this Node implements it, those queries are refused with `503`.
- Policy evaluation, consent governance, and governance audit.
- OPTIONAL Blockchain Adapter behind an application-owned `AuditLedgerPort`.

## Communication boundaries

The Node receives versioned requests and issues explicit decisions/authorization artifacts. Ledger access is an outbound adapter and contains minimized proofs only.

## Non-responsibilities

It does not own raw hospital clinical databases, clinician workflows, patient medical-record editing, company self-approval, or research notebook execution.

## Expected contracts

The consumer-side [`research-authorization-check.v1.yaml`](../../contracts/api/research/research-authorization-check.v1.yaml) contract is IMPLEMENTED for HC-182, but this Node does not provide it yet. Hospital-registry, review/decision, other policy and authorization, audit-event, Federation, and immutable-proof contracts remain PLANNED.
