# Governance Node

## Purpose and status

CONFIRMED Governance / Ethics Authority boundary. Its stack (Python + FastAPI, one process) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED at D2 (HC-130): a FastAPI app with Clean/Hexagonal layers, pinned dependencies, tests, and a liveness `GET /health`. The [hospital approval API](#hospital-approval-api-hc-131) is IMPLEMENTED at D2 (HC-131), over applications and decisions held **in memory**, seeded from fictional demo data: decisions are lost on restart, and the reviewer is declared, not authenticated. Synchronization requests (HC-132), research requests (HC-133), audit (HC-134), policy (HC-135), and consent evaluation (HC-136) are PLANNED, so the Node authorizes no data exchange. There is no persistence, no authentication, and no ledger adapter. It is not deployed.

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

`python main.py` listens on `127.0.0.1:8200`, the ADR-0003 port that the Federation Service already calls (`FEDERATION_GOVERNANCE_URL`). `fastapi dev` and `fastapi run` need `--port 8200`. At startup the Node reads its fictional seed data from the repository's [`demo-data/`](../../demo-data/README.md); set `GOVERNANCE_NODE_DEMO_DATA` to another directory with the same files to change it. A seed file not marked `"fictional": true`, unreadable, or inconsistent stops startup.

## Runtime skeleton (HC-130)

IMPLEMENTED at D2. One process, so there is no per-instance configuration file. The identity is the fictional Governance / Ethics Authority of the demo dataset, set in `main.py`: node `node-governance`, organization `org-governance` ([`demo-data/organizations.json`](../../demo-data/organizations.json)). It is not authenticated.

```text
main.py                                   # composition root: identity, seed data, clock, routers
domain/                                   # NodeIdentity, NodeStatus, HospitalApplication, approval rules
application/get_node_status.py            # use case; declares capabilities as their APIs land
application/hospital_approval.py          # HC-131 use cases and their ports
adapters/inbound/http/health.py           # GET /health
adapters/inbound/http/hospital_approval.py
adapters/outbound/in_memory_hospital_applications.py  # store, seeded from demo-data/governance.json
adapters/outbound/fixture_reviewer_directory.py       # who a reviewer_ref names (demo-data/people.json)
tests/                                    # domain, use case, adapter, HTTP, and layer-boundary tests
```

`GET /health` is a liveness check only:

```json
{
  "status": "ok",
  "node": "governance-node",
  "version": "0.2.0",
  "node_ref": "node-governance",
  "organization_ref": "org-governance",
  "capabilities": ["hospital_approval"],
  "notice": "Governance Node (HC-130, HC-131). ... Liveness only; not a production health check."
}
```

`capabilities` lists the governance APIs served. Every route not documented here answers `404`. In particular, the Federation Service's synchronization authorization check (`POST /v1/synchronization-authorizations/{decision_ref}/checks`) gets `404`, which it treats as unavailable, so it still refuses those queries with `503`. A test checks the exact set of routes served, so each new route must come with its ticket.

`domain/` and `application/` use the standard library only; FastAPI and Pydantic stay in `adapters/` and `main.py`, as the layer-boundary test checks.

## Hospital approval API (HC-131)

IMPLEMENTED at D2. This Node serves [`hospital-approval.v1.yaml`](../../contracts/api/governance/hospital-approval.v1.yaml): the Governance / Ethics Authority, not a company-managed portal, decides whether a hospital joins the ecosystem.

| Route | Purpose |
|---|---|
| `GET /v1/hospital-applications[?status=]` | Applications: `human_review` first, then `pending`, `approved`, `rejected`, newest submission first. `400` for an unknown status. |
| `GET /v1/hospital-applications/{application_ref}` | One application, its findings, and its decision if any. `404 application_not_found`. |
| `POST /v1/hospital-applications/{application_ref}/decision` | Record the reviewer's decision. `201` with the decision. |
| `GET /v1/hospital-approvals/{decision_ref}` | A hospital approval decision by reference, for a consumer that must check a cited approval. Any other reference, including a synchronization or research decision, is `404 decision_not_found`. |

**Findings** are what a reviewer must examine: missing documents, unaccepted agreements, the deterministic completeness check's findings, and the assisted review's findings, which are **advisory** and never decide. Only document metadata is served, never document contents.

**Decision rules** (`domain/hospital_approval.py`, the same rules as the Governance Portal's review form, HC-073), checked in this order:

1. The application is in `human_review` and has no decision; otherwise `409 not_awaiting_review`. A decision cannot be changed or recorded twice, even by two concurrent requests.
2. `reviewer_ref` names a person with the `governance_reviewer` role outside the applicant organization; otherwise `403 reviewer_not_allowed`. An applicant never decides on its own application.
3. The review rules hold; otherwise `422 invalid_decision` listing every broken rule: a rationale of at least 20 characters once trimmed; findings acknowledged (`findings_acknowledged: true`) when there are any; at least one condition to approve an application with missing documents or unaccepted agreements; no condition on a rejection. Blank conditions are dropped.

A malformed body, an unknown or missing field, or a value outside the contract is `400 invalid_request`. The decision reference is `dec-` and the application's suffix (`app-hospital-c` gives `dec-hospital-c`), one decision per application; `decided_at` is the Node's clock, in UTC.

**Storage and identity, at D2:** `InMemoryHospitalApplicationStore` holds the applications and decisions. At startup it loads the hospital applications and their decisions from the fictional [`demo-data/governance.json`](../../demo-data/governance.json), and checks that each decided application cites its own decision with the same outcome. Decisions recorded through the API stay in memory and are **lost on restart**; persistence is OPEN. `FixtureReviewerDirectory` reads the staff and clinicians of the fictional [`demo-data/people.json`](../../demo-data/people.json), never patients or relatives. The reviewer is **declared by the caller, not authenticated**: anyone who can reach the Node can claim to be `usr-olfa`. This is demo-depth behavior, not production security.

Demo, with the Node running (`python main.py`):

```bash
# Hospital C awaits review, with 4 findings.
curl -s 'localhost:8200/v1/hospital-applications?status=human_review'
curl -s localhost:8200/v1/hospital-applications/app-hospital-c

# Pr Olfa Hamdi approves it with a condition: 201, dec-hospital-c.
curl -s -X POST localhost:8200/v1/hospital-applications/app-hospital-c/decision \
  -H 'content-type: application/json' -d '{
  "reviewer_ref": "usr-olfa", "outcome": "approved",
  "rationale": "Dossier conforme, sous réserve de l’attestation d’assurance.",
  "conditions": ["Transmettre l’attestation d’assurance sous 30 jours."],
  "findings_acknowledged": true}'

curl -s localhost:8200/v1/hospital-approvals/dec-hospital-c
```

Other states to show on Hospital C: `reviewer_ref: "usr-mehdi"` (its own manager) gives `403`; `findings_acknowledged: false` with no condition gives `422` with both rules; a second decision gives `409`.

Not done at D2: nothing calls this API yet. The Governance Portal still records simulated decisions in the browser (HC-073), and the Federation Service's node registry still reports approvals `verified: false` without calling `getHospitalApproval`. Application submission and document upload, decision expiry or revocation, Hospital Node configuration and package generation after approval, and recording decisions in the governance audit trail (HC-134) or a ledger are out of scope.

## Responsibilities and owned concepts

- Hospital approval and registry. Hospital approval is served by the [hospital approval API](#hospital-approval-api-hc-131) (HC-131). The Federation Service's node registry ([`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml), HC-142) is only a routing directory: each registration cites a Governance approval decision, which it could now check with `getHospitalApproval`, but does not yet.
- Synchronization and research authorization. The Federation Service already calls [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) on this Node before every synchronization-decision query (HC-144); until this Node implements it, those queries are refused with `503`.
- Policy evaluation, consent governance, and governance audit.
- OPTIONAL Blockchain Adapter behind an application-owned `AuditLedgerPort`.

## Communication boundaries

The Node receives versioned requests and issues explicit decisions/authorization artifacts. Ledger access is an outbound adapter and contains minimized proofs only.

## Non-responsibilities

It does not own raw hospital clinical databases, clinician workflows, patient medical-record editing, company self-approval, or research notebook execution.

## Expected contracts

The consumer-side [`research-authorization-check.v1.yaml`](../../contracts/api/research/research-authorization-check.v1.yaml) contract is IMPLEMENTED for HC-182, but this Node does not provide it yet. This Node provides [`hospital-approval.v1.yaml`](../../contracts/api/governance/hospital-approval.v1.yaml) (HC-131). Synchronization and research review/decision, other policy and authorization, audit-event, Federation, and immutable-proof contracts remain PLANNED.
