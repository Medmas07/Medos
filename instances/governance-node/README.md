# Governance Node

## Purpose and status

CONFIRMED Governance / Ethics Authority boundary. Its stack (Python + FastAPI, one process) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED at D2 (HC-130): a FastAPI app with Clean/Hexagonal layers, pinned dependencies, tests, and a liveness `GET /health`. The [hospital approval API](#hospital-approval-api-hc-131) is IMPLEMENTED at D2 (HC-131), over applications and decisions held **in memory**, seeded from fictional demo data: decisions are lost on restart, and the reviewer is declared, not authenticated. The [synchronization request API](#synchronization-request-api-hc-132) and the synchronization authorization check the Federation Service calls are IMPLEMENTED at D2 (HC-132), in memory the same way; patient grants are checked against fictional demo grants (**MOCKED**). The [research access request API](#research-access-request-api-hc-133) and the research authorization check the Research Service calls are IMPLEMENTED at D2 (HC-133), in memory the same way. The [governance audit API](#governance-audit-api-hc-134) is IMPLEMENTED at D2 (HC-134): the Node records the requests it receives, the decisions it records, and every authorization check it answers in its own minimized audit trail, in memory the same way. The [governance policy engine](#governance-policy-engine-hc-135) is IMPLEMENTED at D3 (HC-135): the Authority's review rules are a versioned, effective-dated policy, read from fictional data at startup; every review and decision applies the version in effect and every decision cites it. The policy is a fictional demo policy, not a validated legal or ethical framework, and new versions are published by editing the data and restarting. [Consent policy evaluation](#consent-policy-evaluation-hc-136) is IMPLEMENTED at D3 (HC-136): a synchronization's patient grant is evaluated against the grants of the Hospital Node holding it, over real HTTP, when reviewing and again before each exchange; a grant revoked there stops the authorization. The demo Hospital Nodes' grant stores are themselves MOCKED. The [`AuditLedgerPort`](#audit-ledger-port-hc-190) is defined (HC-190, D1) and the [simulated immutable ledger](#simulated-immutable-ledger-hc-191) behind it is IMPLEMENTED at D2 (HC-191): every decision recorded is anchored as a minimized proof, served by a read-only proofs API. The ledger is **MOCKED**: an append-only list in memory, not a blockchain. There is no persistence and no authentication. It is not deployed.

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

Patient grants (HC-136) are asked of the Hospital Nodes listed in [`hospital-nodes.demo.json`](hospital-nodes.demo.json) (Hospital A `8101`, Hospital B `8102`, private practice `8104`); set `GOVERNANCE_HOSPITAL_NODES` to another directory file. Without those nodes running, consent checks fail as unavailable. `GOVERNANCE_GRANTS=fixture` reads the fictional `access.json` instead (**MOCKED**, for demos without Hospital Nodes); any value other than `http` (default) or `fixture` stops startup.

## Runtime skeleton (HC-130)

IMPLEMENTED at D2. One process, so there is no per-instance configuration file. The identity is the fictional Governance / Ethics Authority of the demo dataset, set in `main.py`: node `node-governance`, organization `org-governance` ([`demo-data/organizations.json`](../../demo-data/organizations.json)). It is not authenticated.

```text
main.py                                   # composition root: identity, seed data, clock, routers
domain/                                   # NodeIdentity, NodeStatus, HospitalApplication, approval rules,
                                          # synchronization and research requests, checks, authorization,
                                          # audit events, GovernancePolicy and PolicyHistory
application/get_node_status.py            # use case; declares capabilities as their APIs land
application/hospital_approval.py          # HC-131 use cases and their ports
application/synchronization.py            # HC-132 use cases and their ports
application/research.py                   # HC-133 use cases and their ports
application/audit.py                      # HC-134 use cases and the AuditTrail port the others record to
application/policy.py                     # HC-135 use cases: the policy versions and their status
application/ledger.py                     # HC-190 AuditLedgerPort and anchoring use cases
adapters/inbound/http/health.py           # GET /health
adapters/inbound/http/hospital_approval.py
adapters/inbound/http/synchronization_requests.py
adapters/inbound/http/sync_authorization.py   # the Federation Service's check
adapters/inbound/http/research_requests.py
adapters/inbound/http/research_authorization.py   # the Research Service's check
adapters/inbound/http/audit_events.py     # GET /v1/audit/events[/{event_ref}]
adapters/inbound/http/policies.py         # GET /v1/policies[/{policy_ref}]
adapters/inbound/http/ledger_proofs.py    # GET /v1/ledger/proofs, GET /v1/audit/events/{event_ref}/proof
adapters/inbound/http/problems.py         # RFC 9457 problem details
adapters/outbound/in_memory_hospital_applications.py  # store, seeded from demo-data/governance.json
adapters/outbound/fixture_reviewer_directory.py       # who a reviewer_ref names (demo-data/people.json)
adapters/outbound/in_memory_synchronization.py        # store, seeded from demo-data/governance.json
adapters/outbound/http_patient_grants.py              # HC-136: patient grants from the holder's Hospital Node
adapters/outbound/fixture_patient_grants.py           # MOCKED, opt-in: patient grants (demo-data/access.json)
hospital-nodes.demo.json                              # which Hospital Node holds each organization's grants
adapters/outbound/in_memory_research.py               # store, seeded from governance.json and research.json
adapters/outbound/in_memory_audit_trail.py            # trail, seeded from governance.json
adapters/outbound/fixture_policies.py                 # policy versions, read from governance.json
adapters/outbound/simulated_audit_ledger.py           # HC-191 MOCKED ledger, seeded from governance.json
tests/                                    # domain, use case, adapter, HTTP, and layer-boundary tests
```

`GET /health` is a liveness check only:

```json
{
  "status": "ok",
  "node": "governance-node",
  "version": "0.8.0",
  "node_ref": "node-governance",
  "organization_ref": "org-governance",
  "capabilities": ["hospital_approval", "synchronization", "research", "audit", "policy", "ledger"],
  "grants": "http",
  "notice": "Governance Node (HC-130 to HC-136, HC-191). ... Liveness only; not a production health check."
}
```

`capabilities` lists the governance APIs served. Every route not documented here answers `404`. A test checks the exact set of routes served, so each new route must come with its ticket.

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
3. The review rules hold; otherwise `422 invalid_decision` listing every broken rule: a rationale of at least the [policy](#governance-policy-engine-hc-135)'s minimum length once trimmed (20 in v1); findings acknowledged (`findings_acknowledged: true`) when there are any; at least one condition to approve an application with missing documents or unaccepted agreements; no condition on a rejection. Blank conditions are dropped.

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

Not done at D2: nothing calls this API yet. The Governance Portal still records simulated decisions in the browser (HC-073), and the Federation Service's node registry still reports approvals `verified: false` without calling `getHospitalApproval`. Application submission and document upload, decision expiry or revocation, and Hospital Node configuration and package generation after approval are out of scope. Each decision recorded through the API is added to the [governance audit trail](#governance-audit-api-hc-134) and anchored in the [simulated ledger](#simulated-immutable-ledger-hc-191).

## Synchronization request API (HC-132)

IMPLEMENTED at D2. Hospital Nodes must not synchronize patient data freely: a hospital asks the Authority, which approves or rejects, and an approval is a **temporary authorization** the Federation Service checks before each exchange.

| Route | Contract | Purpose |
|---|---|---|
| `POST /v1/synchronization-requests` | [`synchronization-requests.v1.yaml`](../../contracts/api/governance/synchronization-requests.v1.yaml) | Submit a request: requester and target organizations, pseudonymous patient, purpose, scope (`encounters`, `medications`, `lab_reports`), duration (1–365 days), and consent basis. Recorded `pending` as `sync-NNN`. |
| `GET /v1/synchronization-requests[?status=]` | same | Requests with their status **as of now**: `pending`, `active`, `expired` (approved but ended: authorizes nothing), `rejected`; pending first, newest submission first. |
| `GET /v1/synchronization-requests/{request_ref}` | same | One request, the Node's three checks, the longest approval possible now, and its decision. |
| `POST /v1/synchronization-requests/{request_ref}/decision` | same | Record the reviewer's decision. |
| `POST /v1/synchronization-authorizations/{decision_ref}/checks` | [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) | The Federation Service's question: does this decision authorize this exchange now? |

**Checks** (`domain/synchronization.py`, the same rules as the Governance Portal's synchronization form, HC-076), evaluated when answering:

- **organizations:** requester and target are distinct and both approved by this Node's own [hospital approvals](#hospital-approval-api-hc-131). Approving Hospital C there makes it eligible here.
- **consent:** a `patient_grant` must name a grant that exists, is not revoked, has not expired, concerns this patient, and covers the requested scope. A basis the [policy](#governance-policy-engine-hc-135) in effect does not accept fails; one it marks `manual` (in v1, `signed_consent_form` and `emergency_override`) cannot be verified by the Node, so the reviewer must confirm it. `none` fails.
- **duration:** the approval lasts at most the requested duration, never beyond the policy's longest synchronization (365 days in v1) or the patient grant (whole days left). It fails when no day is left.

**Decision rules**, in this order: `409 not_pending` unless the request is pending; `403 reviewer_not_allowed` unless the reviewer is a `governance_reviewer` outside both organizations; `422 invalid_decision` listing every broken rule. Those rules are a rationale of at least the policy's minimum length (20 in v1); for an approval, every check passing (otherwise only a rejection is possible), `manual` checks confirmed, and `approved_days` between 1 and the maximum; for a rejection, no condition and no duration. The decision is `dec-` and the request reference; an approval is valid from the decision for `approved_days`.

**Authorization check:** deny by default, with the first failing reason, in this order: `not_found` (unknown, not a synchronization decision, or the request is still pending), `not_approved`, `not_yet_valid`, `expired`, `requester_mismatch`, `patient_mismatch`, `scope_exceeded` (the asked scope must be inside the approved one), and `purpose_mismatch`. An authorization lists the target organization as the only one the requester may query. A denial is a `200` result. Every answer is recorded with `actor_ref` in the [governance audit trail](#governance-audit-api-hc-134) before it is given, and, last, `revoked`: the patient grant the approval relies on is no longer active at the Hospital Node holding it ([HC-136](#consent-policy-evaluation-hc-136)). If that node cannot answer, the check answers `503 consent_unavailable` and nothing is authorized. A decision itself cannot be revoked yet.

**Storage and sources, at D2:**

- `InMemorySynchronizationStore` holds requests and decisions. It is seeded from the fictional [`demo-data/governance.json`](../../demo-data/governance.json), checks each decided request against its decision, and records a decision atomically. Everything recorded through the API is **lost on restart**.
- Patient grants are recorded and enforced by each Hospital Node ([`patient-access-grants.v1.yaml`](../../contracts/api/patient-access/patient-access-grants.v1.yaml), HC-115), not here. Since HC-136 the Node asks the Hospital Node holding a grant over HTTP ([consent policy evaluation](#consent-policy-evaluation-hc-136)). `FixturePatientGrantDirectory` (`GOVERNANCE_GRANTS=fixture`, the default of `create_app` in tests) is **MOCKED**: it reads the fictional [`demo-data/access.json`](../../demo-data/access.json), read-only, and never sees a grant recorded or revoked on a Hospital Node at runtime.
- `submitted_by_ref` and `reviewer_ref` are declared by the caller, **not authenticated**.

Demo, demo step 20, with the Node running:

```bash
# sync-001 is pending; Patient A's grant caps an approval at 13 days.
curl -s localhost:8200/v1/synchronization-requests/sync-001

# Before any decision, the Federation's check is denied (not_found).
curl -s -X POST localhost:8200/v1/synchronization-authorizations/dec-sync-001/checks \
  -H 'content-type: application/json' -d '{"requester_organization_ref": "org-hospital-a",
  "actor_ref": "clin-x", "patient_ref": "pat-a", "scope": ["medications"],
  "purpose": "Continuité des soins : consultation de cardiologie"}'

# Pr Olfa Hamdi approves it for 13 days: 201, dec-sync-001.
curl -s -X POST localhost:8200/v1/synchronization-requests/sync-001/decision \
  -H 'content-type: application/json' -d '{"reviewer_ref": "usr-olfa", "outcome": "approved",
  "rationale": "Finalité de soins, périmètre limité, autorisation du patient active.",
  "conditions": [], "approved_days": 13, "manual_checks_confirmed": false}'
```

The same check then answers `authorized`, naming `org-hospital-b`. Other states to show: `approved_days: 30` gives `422`; `reviewer_ref: "clin-x"` (of the requesting hospital) gives `403`; the check for `dec-sync-002` is `expired`, and for `dec-sync-003` `not_approved`.

**End to end**, with Hospital Nodes A and B, the Federation Service (`http` mode, demo registry seed), and this Node running as separate processes, a federated query for Patient A under `dec-sync-001`:

1. Before the decision, it is refused (`403`) and no Hospital Node is asked.
2. After the decision, the Federation Service asks Hospital B only.
3. Hospital B still answers `denied`: its MOCKED verifier reads the fixture decisions and does not know a decision recorded here at runtime.

How a Hospital Node verifies a decision with the Governance Node is OPEN ([OPEN_QUESTIONS.md](../../docs/OPEN_QUESTIONS.md)).

Not done at D2: the Governance Portal still records simulated synchronization decisions (HC-076) and does not call this API; revoking or extending an approval. Decisions are anchored in the [simulated ledger](#simulated-immutable-ledger-hc-191) (MOCKED) since HC-191.

## Research access request API (HC-133)

IMPLEMENTED at D2. Research uses Compute-to-Data: a project asks the Authority for access, and an approval authorizes code to run inside the named Hospital Nodes, with only controlled aggregates leaving them. The Research Service checks the approval before each job.

| Route | Contract | Purpose |
|---|---|---|
| `POST /v1/research-requests` | [`research-requests.v1.yaml`](../../contracts/api/governance/research-requests.v1.yaml) | Submit a request with the project's content: title, research organization, principal investigator, purpose, participating organizations, structured data scope, and protocol reference. Recorded `under_review` as `rar-NNN`. |
| `GET /v1/research-requests[?status=]` | same | Requests with their status **as of now**: `under_review`, `authorized`, `expired` (authorizes nothing), `rejected`; under review first, newest submission first. |
| `GET /v1/research-requests/{request_ref}` | same | One request, the Node's checks, the organizations an approval may name now, and its decision. |
| `POST /v1/research-requests/{request_ref}/decision` | same | Record the reviewer's decision. |
| `POST /v1/research-authorizations/check` | [`research-authorization-check.v1.yaml`](../../contracts/api/research/research-authorization-check.v1.yaml) | The Research Service's question before each job: does this decision authorize this exact job now? |

**Data scope.** A request carries its population as bounds (`age_min`, `age_max`, `encounter_from`, `encounter_to`, at least one, lower never above upper) and its variables as contract names (`hba1c`, `age_band`), the same shape the Research Service and Hospital Nodes use. The demo projects carry this in a `dataScope` added to [`demo-data/research.json`](../../demo-data/research.json); their French variable labels stay for display.

**Checks** (`domain/research.py`, the same rules as the Governance Portal's research form, HC-078), evaluated when answering:

- **protocol:** a protocol document reference is provided (document contents never reach the Node).
- **organizations:** at least one participating organization is approved by this Node's own [hospital approvals](#hospital-approval-api-hc-131); only those are eligible.

**Decision rules**, in this order:

1. `409 not_under_review` unless the request is under review.
2. `403 reviewer_not_allowed` unless the reviewer is a `governance_reviewer` who is neither the submitter nor the principal investigator, and belongs neither to the research organization nor to a participating one.
3. `422 invalid_decision` listing every broken rule:
   - a rationale of at least the [policy](#governance-policy-engine-hc-135)'s minimum length (20 in v1);
   - for an approval: every check passing, at least one eligible organization and only those, at least one requested variable and only those, a validity of 1 month to the policy's longest (12 calendar months in v1), and a minimum output cell size of at least the policy's (10 in v1, as in `dec-rar-001`);
   - for a rejection: nothing authorized and no condition.

An approval only narrows the request: the population stays the one requested. The decision is `dec-` and the request reference.

**Authorization check.** An unknown reference, a request still under review, or a decision on another subject is `404 decision_not_found`. Otherwise the answer is `approved`, with the decision's organizations, variables, and `valid_until`, or `denied` with the first failing `reason_code`, in this order: `not_approved`, `not_yet_valid`, `expired`, `project_mismatch`, `requester_mismatch` (the principal investigator or the submitter only), `organization_not_approved`, `variable_not_approved`, and `population_exceeded`. Every bound of the job must lie inside the requested population, and a bound the job leaves open where the request set one is wider. `purpose` is not compared. The decision's minimum cell size is not carried by this contract, so the Research Service's job sets its own output policy (OPEN).

**Storage, at D2:** `InMemoryResearchStore` holds requests and decisions, seeded from the fictional [`demo-data/governance.json`](../../demo-data/governance.json) (requests and decisions, with the structured `researchAuthorization` of `dec-rar-001`) and `research.json` (each request's project content). Everything recorded through the API is **lost on restart**, and `submitted_by_ref` and `reviewer_ref` are declared, **not authenticated**.

Demo, with the Node running:

```bash
# rar-002 (asthma study) awaits review; Hospital B and the private practice are eligible.
curl -s localhost:8200/v1/research-requests/rar-002

# Pr Olfa Hamdi approves it narrowed: Hospital B, two variables, 6 months, cell size 10.
curl -s -X POST localhost:8200/v1/research-requests/rar-002/decision \
  -H 'content-type: application/json' -d '{"reviewer_ref": "usr-olfa", "outcome": "approved",
  "rationale": "Protocole conforme, finalité de recherche et périmètre proportionné.",
  "conditions": [], "approved_organization_refs": ["org-hospital-b"],
  "approved_variables": ["consultation_month", "age_band"], "validity_months": 6,
  "minimum_cell_size": 10}'

# The Research Service's check for job-001 under dec-rar-001: approved.
curl -s -X POST localhost:8200/v1/research-authorizations/check \
  -H 'content-type: application/json' -d '{"decision_ref": "dec-rar-001",
  "project_ref": "proj-001", "requested_by": "usr-aymen",
  "purpose": "Aggregate cardiometabolic risk research",
  "target_organization_refs": ["org-hospital-a", "org-hospital-b"],
  "data_scope": {"population": {"age_min": 40, "age_max": 79,
  "encounter_from": "2024-01-01", "encounter_to": "2026-12-31"},
  "variables": ["age_band", "hba1c"]}}'
```

Other states to show: `reviewer_ref: "usr-aymen"` (the investigator) gives `403`; adding `"diagnosis"` to the variables or a cell size of 5 gives `422`; a check asking for `"diagnosis"` is `denied` with `variable_not_approved`.

**End to end**, with the Research Service, Hospital Nodes A and B, and this Node running as separate processes:

- A request whose scope the HC-183 aggregate can run (`hba1c`, encounter dates only) is submitted and approved here. A job under it is authorized, and both nodes execute it with output validation passed. The aggregate is suppressed because the fictional cohorts are below the minimum cell size of 10.
- Jobs outside a decision are denied here before any node is asked.
- Under `dec-rar-001`, no job can complete. The HC-183 aggregate refuses age bounds (no local demographic data), and this Node refuses a job without them as wider than the approved population (ages 40–79).

Not done at D2: the Governance Portal still records simulated research decisions (HC-078), and the Research Portal does not submit to this API; revoking or extending an approval. Decisions are anchored in the [simulated ledger](#simulated-immutable-ledger-hc-191) (MOCKED) since HC-191.

## Governance audit API (HC-134)

IMPLEMENTED at D2. The Node serves [`governance-audit-events.v1.yaml`](../../contracts/api/governance/governance-audit-events.v1.yaml): the trail of what the Governance / Ethics Authority itself did. It is this Node's trail only; each Hospital Node keeps its own ([`hospital-audit-events.v1.yaml`](../../contracts/api/hospital-audit/hospital-audit-events.v1.yaml)).

| Route | Purpose |
|---|---|
| `GET /v1/audit/events[?domain=&action=&organization_ref=&subject_ref=&limit=]` | Events newest first (the later recorded first at the same time), filters combined, `limit` 1–500 (50 by default). An unknown, repeated, or invalid parameter is `400 invalid_request`. |
| `GET /v1/audit/events/{event_ref}` | One event. `404 event_not_found`. |

**What is recorded**, by the use cases themselves (`application/`), through the `AuditTrail` port:

| Action | When | Actor | Organizations |
|---|---|---|---|
| `request_received` | a synchronization or research request is submitted | `submitted_by_ref` | requester and target; or research organization and participating ones |
| `decision_recorded` | a hospital approval, synchronization, or research decision is recorded, with its outcome | `reviewer_ref` | the Authority, then those of the subject |
| `authorization_checked` | the Federation Service's or the Research Service's check is answered, `authorized` or `denied` with its reason code | `actor_ref` or `requested_by` | the Authority, the requester (Federation) or the targets asked (Research), and an authorized target |
| `application_submitted` | seed events only: no submission API exists | the applicant | the applicant |

**Minimized.** An event holds references, the action, the outcome and reason code, and organizations. It never holds a patient reference, a purpose, a rationale, a data scope, or a document; the subject's reference leads to them through the API that owns them.

**Not recorded:** an invalid request (`400`), a refused decision (`403`, `409`, `422`), and a research check on an unknown decision (`404`): nothing was decided or answered. A synchronization check on an unknown decision is a `200` denial (`not_found`) by its contract, so it is recorded.

**No audit, no answer.** A check is recorded before it is answered; if recording fails, the request fails and authorizes nothing (the Research Service fails closed). A submission or decision is stored first, then recorded: in memory recording cannot fail, but the two stores are not one transaction, so a durable trail would need that settled (OPEN).

**Storage, at D2:** `InMemoryAuditTrail` holds the events, append-only, numbered `evt-NNN`. At startup it loads the seven fictional events of [`demo-data/governance.json`](../../demo-data/governance.json), taking a decision event's domain and outcome from the decision it names. Events recorded at runtime are **lost on restart** (`durable: false`). Actors are those the callers declare, **not authenticated**, and readers are not authenticated either; who may read the trail and retention are OPEN. Each `decision_recorded` event is anchored in the [simulated ledger](#simulated-immutable-ledger-hc-191) (HC-191, MOCKED); its proof is served by the ledger proofs API, not this one. The Governance Portal's ledger proofs remain fixtures (MOCKED BLOCKCHAIN, HC-080).

Demo, with the Node running:

```bash
# The seven seed events, newest first; those concerning Hospital B.
curl -s localhost:8200/v1/audit/events
curl -s 'localhost:8200/v1/audit/events?organization_ref=org-hospital-b'

# The Federation's check before any decision on sync-001: denied (not_found) and audited.
curl -s -X POST localhost:8200/v1/synchronization-authorizations/dec-sync-001/checks \
  -H 'content-type: application/json' -d '{"requester_organization_ref": "org-hospital-a",
  "actor_ref": "clin-x", "patient_ref": "pat-a", "scope": ["medications"],
  "purpose": "Continuité des soins : consultation de cardiologie"}'

# After Pr Olfa Hamdi's approval (see the synchronization demo) and the same check again:
curl -s 'localhost:8200/v1/audit/events?subject_ref=dec-sync-001'
```

The last call lists the authorized check, the decision, and the denied check, none naming the patient. Other states to show: `?limit=0` or `?patient_ref=pat-a` gives `400`; `evt-999` gives `404`; after a restart only the seven seed events remain.

Not done at D2: the Governance Portal's audit timeline (HC-079) still reads fixtures and local state and does not call this API; persistence, retention, authenticated readers and actors, auditing refused decisions, and anchoring events other than decisions.

## Governance policy engine (HC-135)

IMPLEMENTED at D3. The Governance / Ethics Authority's rules for every decision are a **policy**: versioned data owned by this Node, served by [`governance-policies.v1.yaml`](../../contracts/api/governance/governance-policies.v1.yaml), and applied by a deterministic engine (`domain/policy.py`) in the existing reviews and decisions. No AI or clinical judgment is involved.

| Route | Purpose |
|---|---|
| `GET /v1/policies` | Every version, the latest first, with its status now: `scheduled`, `in_effect`, or `superseded`. |
| `GET /v1/policies/{policy_ref}` | One version, as a decision cites it. `404 policy_not_found`. |

**Rules.** These were constants in the code; they are now the policy's values (v1 keeps the same values, so behavior is unchanged):

| Rule | Applied by | v1 |
|---|---|---|
| `review.minimum_rationale_length` | every decision (HC-131 to HC-133) | 20 |
| `synchronization.maximum_duration_days` | the synchronization `duration` check and `max_approved_days`: an approval never exceeds it | 365 |
| `synchronization.consent_bases` | the synchronization `consent` check: a basis not listed fails; `verified` (patient grant only) is checked by the Node; `manual` is confirmed by the reviewer | `patient_grant` verified, `signed_consent_form` and `emergency_override` manual |
| `research.maximum_validity_months` | a research approval's `validity_months` | 12 |
| `research.minimum_cell_size` | a research approval's `minimum_cell_size` | 10 |

**Engine.**

- **Version in effect.** Each review and decision uses the latest version whose `effective_from` has passed on the Node's clock. Request details show checks under the version in effect when answering.
- **Cited.** Every decision records `policy_ref`, the version it was decided under, in the three decision contracts (now `1.1.0`). The seed decisions cite `pol-governance-v1` (`policyId` in [`demo-data/governance.json`](../../demo-data/governance.json)), and `check_fixtures.py` verifies each cites the version in effect when it was decided.
- **No retroactive effect.** A new version never changes, extends, or revokes a decision already made; the authorization checks of HC-132 and HC-133 keep answering from the decision.
- **Stricter only.** A version may only tighten the limits the contracts document: rationale at least 20, synchronization at most 365 days, research validity at most 12 months, cell size at least 10, `none` never accepted, and only a patient grant `verified`. A version that breaks this, versions out of order, or a file not marked fictional stops startup.

**Storage and authority, at D3:** `load_policies` reads the versions from the fictional `governance.json` once at startup; they never change while the Node runs. Publishing a version means adding it to the data and restarting. Who writes and approves a version, and through which interface, is OPEN; there is no policy-editing API. Readers are not authenticated. The demo policy is fictional, not a validated legal or ethical framework.

Demo, with the Node running:

```bash
# The one demo version, in effect, and its rules.
curl -s localhost:8200/v1/policies

# A research approval looser than the policy is refused: 422 on validity_months and minimum_cell_size.
curl -s -X POST localhost:8200/v1/research-requests/rar-002/decision \
  -H 'content-type: application/json' -d '{"reviewer_ref": "usr-olfa", "outcome": "approved",
  "rationale": "Protocole conforme, finalité de recherche et périmètre proportionné.",
  "conditions": [], "approved_organization_refs": ["org-hospital-b"],
  "approved_variables": ["consultation_month", "age_band"], "validity_months": 13,
  "minimum_cell_size": 5}'
```

With `validity_months: 6` and `minimum_cell_size: 10` the same decision is recorded, citing `pol-governance-v1`. To show a version change, set `GOVERNANCE_NODE_DEMO_DATA` to a copy of `demo-data/` whose `governance.json` adds a stricter version 2 effective in the near future: before that time the Node reviews `sync-001` under v1 (13 days possible); after it, under v2 (for example 10 days at most), and decisions then cite v2 while earlier ones keep citing v1. `tests/test_policies_http.py` runs exactly this.

Not done at D3: a policy-editing or approval workflow, rules beyond those listed (purposes, variables, organizations), recording the policy version in the audit trail or a ledger, the Governance Portal displaying the policy (its forms still apply their own D1 constants), and consent evaluation (HC-136).

## Consent policy evaluation (HC-136)

IMPLEMENTED at D3. A synchronization relying on a `patient_grant` is evaluated against the grants of the **Hospital Node of the target organization**: that node holds the records exchanged, records the patient's grants, and enforces them ([`patient-access-grants.v1.yaml`](../../contracts/api/patient-access/patient-access-grants.v1.yaml), HC-115). The Governance Node asks it, over real HTTP, `GET /v1/patients/{patient_ref}/access-grants`, and stores no grant: the node stays the source of truth.

| When | What the Node does with the holder's answer |
|---|---|
| Reading or deciding a request (`synchronization-requests.v1.yaml`, now `1.2.0`) | The `consent` check passes only if the grant exists there for this patient, is not revoked, has not expired, and covers the scope; the approval never outlasts it. If the node cannot answer, the check **fails** with the reason, and only a rejection is possible. |
| Each Federation authorization check (`sync-authorization-check.v1.yaml`, now `1.1.0`) | Once every other check passes, the grant is asked again. Revoked, expired, or unknown there: `denied` with `revoked`. Node unable to answer: `503 consent_unavailable`; the Federation Service asks no node. Both are audited as denials (`revoked`, `consent_unavailable`). |

Which bases are accepted, and which are verified this way, is the [policy](#governance-policy-engine-hc-135)'s `synchronization.consent_bases`: in v1 only `patient_grant` is verified; `signed_consent_form` and `emergency_override` are confirmed by the reviewer and never asked of a node. A denial reached before consent, such as an expired decision, does not ask the node.

**Boundaries.** This is a call to a Hospital Node's own consent API, not to a DMI, and only for the organization a request names. The Governance Node receives grant metadata only: references, scope, purpose, and times; nothing clinical. The answer is parsed strictly: another organization or patient, a grant of another patient, a time without offset, an error, a 2-second timeout, or an organization missing from the directory makes the consent unavailable (deny by default).

**At D3:** the directory of nodes is a fictional file ([`hospital-nodes.demo.json`](hospital-nodes.demo.json), `GOVERNANCE_HOSPITAL_NODES`); production discovery, and authentication between the Governance Node and Hospital Nodes, are OPEN. The demo Hospital Nodes' grant stores are **MOCKED** (in memory, seeded from fictional data): the integration is real, the grants are fictional. A grant held only by another node than the target is not seen, and propagating one patient's consent to every node holding their records remains OPEN. `GOVERNANCE_GRANTS=fixture` keeps the HC-132 MOCKED behavior.

Demo, with Hospital Node B (`HOSPITAL_NODE_CONFIG=config/hospital-b.demo.json python main.py` in `instances/hospital-node/`) and this Node running:

```bash
# The consent check of sync-001 is answered by Hospital B: pass, 13 days at most.
curl -s localhost:8200/v1/synchronization-requests/sync-001
# Approve it as in the synchronization demo, then the Federation's check is authorized.
# Patient A revokes the grant on Hospital B:
curl -s -X POST localhost:8102/v1/patients/pat-a/access-grants/grant-a-drx/revocation
# The same check is now denied: revoked. Stop Hospital B and it answers 503 consent_unavailable.
curl -s 'localhost:8200/v1/audit/events?subject_ref=dec-sync-001'
```

**End to end**, with Hospital Nodes A and B, the Federation Service (`http` mode, demo registry seed), and this Node as separate processes: after `dec-sync-001`, a federated query under it asks Hospital B only; after Patient A revokes `grant-a-drx` on Hospital B, the same query is refused `403` with *The Governance Node denied the synchronization authorization: revoked*, and no node is asked.

Not done at D3: authenticated node-to-node calls, node discovery from the Federation registry, consent propagation across nodes, a consent record kept by Governance, verifying the grant's grantee or purpose against the request, and consent for research (research uses aggregates under Compute-to-Data and cites no patient grant).

## Audit ledger port (HC-190)

IMPLEMENTED at D1, as a boundary. [`application/ledger.py`](application/ledger.py) owns the OPTIONAL `AuditLedgerPort` through which a ledger adapter anchors governance proofs. Its only adapter is the [simulated immutable ledger](#simulated-immutable-ledger-hc-191) (HC-191, MOCKED); no real ledger implements it.

**What may be anchored** ([`domain/ledger.py`](domain/ledger.py)): `proof_payload` turns a `decision_recorded` audit event into a `ProofPayload` of six fields only: the event reference, the decision reference, the outcome, the time decided, the organizations (the Authority first), and the payload version (`1`). These are the fields the demo ledger proofs of [`demo-data/governance.json`](../../demo-data/governance.json) anchor, and the seed events `evt-003` and `evt-004` give exactly those payloads. The actor is not anchored. The type has no field for a patient reference, a purpose, a rationale, a data scope, or clinical content, so none can reach a ledger through it. Requests received and authorization checks are not anchorable (`NotAnchorable`).

| Port member | Contract |
|---|---|
| `anchor(payload) -> LedgerProof` | Anchors append-only and returns the receipt: proof reference, payload, ledger name, time anchored. Raises `LedgerUnavailable` when nothing was anchored. |
| `proof(event_ref) -> LedgerProof \| None` | The proof anchoring an event, if any. Raises `LedgerUnavailable`. |
| `proofs() -> list[LedgerProof]` | Every proof, in the order anchored (added by HC-191 to serve them). Raises `LedgerUnavailable`. |
| `simulated` | Whether proofs are held by a simulation rather than a real ledger, so a simulation is never shown as a real ledger. |

**Use cases:** `anchor_decision` anchors a recorded decision once: anchoring it again returns its proof, and the same event with another payload is a `ProofConflict`. `anchor_recorded` is what the decision use cases call after recording a decision (HC-191): the decision stands whatever happens, and a ledger that is unavailable leaves it unanchored. `get_proof` raises `ProofNotFound` for an event without proof; `list_proofs` lists them, the latest anchored first. They are tested against a test double that stays in `tests/` (`test_ledger.py`, `test_ledger_use_cases.py`); the layer test keeps any ledger library out of `domain/` and `application/`.

Not done: hashing the payload (HC-192), a real permissioned ledger (HC-194, after the technology evaluation HC-193; the technology is OPEN), and signatures.

## Simulated immutable ledger (HC-191)

IMPLEMENTED at D2, **MOCKED**. [`adapters/outbound/simulated_audit_ledger.py`](adapters/outbound/simulated_audit_ledger.py) implements the `AuditLedgerPort` as an append-only list in this process's memory, named `local-simulation`, with `simulated: true`. It is **not a blockchain and not a real ledger**: no consensus, signature, replication, hashing, or durability. Proofs anchored at runtime are **lost on restart**. "Immutable" means only that nothing changes or removes a proof once anchored: an event is anchored once, the same payload again returns the same proof, and another payload for the same event is refused (`ProofConflict`), even under concurrent calls.

**Anchoring.** Each hospital approval, synchronization, or research decision recorded through the APIs (HC-131 to HC-133) is stored, recorded in the audit trail as `decision_recorded`, and then anchored: its [six-field minimized payload](#audit-ledger-port-hc-190) becomes the next `proof-NNN`, at the Node's clock time. A refused decision (`403`, `409`, `422`) records nothing, so it anchors nothing. Requests received and authorization checks are never anchored. The decision stands whether or not it was anchored; an unanchored decision is not retried (OPEN). The simulated ledger is always available, so at D2 this never happens.

**Seed.** At startup the ledger loads the two fictional simulated proofs of [`demo-data/governance.json`](../../demo-data/governance.json) (`proof-003` for `evt-003`, `proof-004` for `evt-004`). Each must be marked simulated in `local-simulation`, anchor exactly the six payload fields, and match the payload of the seed audit event it names; otherwise startup stops. The seed decisions `evt-001`, `evt-002`, and `evt-005` have no proof in the demo data and stay unanchored. The fixtures' `hash` is not read: hashing is HC-192.

| Route | Contract | Purpose |
|---|---|---|
| `GET /v1/ledger/proofs` | [`governance-ledger-proofs.v1.yaml`](../../contracts/api/governance/governance-ledger-proofs.v1.yaml) | Every proof, the latest anchored first, with `simulated` and a MOCKED BLOCKCHAIN notice. |
| `GET /v1/audit/events/{event_ref}/proof` | same | The proof anchoring one audit event. `404 event_not_found` for an unknown event; `404 proof_not_found` for an event without proof. |

Either route answers `503 ledger_unavailable` if the ledger cannot be read; the simulated ledger always can. A proof carries the proof reference, the ledger name, the time anchored, and the payload, never the actor, a patient reference, a purpose, a rationale, a scope, or clinical content. Readers are not authenticated.

Demo, with the Node running (`GOVERNANCE_GRANTS=fixture python main.py` to run without Hospital Nodes):

```bash
# The two simulated seed proofs.
curl -s localhost:8200/v1/ledger/proofs

# Approve sync-001 as in the synchronization demo (201): it is recorded as evt-008 ...
curl -s 'localhost:8200/v1/audit/events?subject_ref=dec-sync-001'
# ... and anchored at once as proof-005, with its minimized payload only.
curl -s localhost:8200/v1/audit/events/evt-008/proof
```

Other states to show: `evt-007` (a request received) and `evt-001` (a seed decision without a demo proof) give `404 proof_not_found`; `evt-999` gives `404 event_not_found`; a second decision on `sync-001` gives `409` and anchors nothing; after a restart only `proof-003` and `proof-004` remain.

Not done at D2: payload hashing and verification (HC-192), a real permissioned ledger (HC-193, HC-194), signatures, durability, retrying an unanchored decision, anchoring the policy version, and the Governance Portal reading these proofs (its proof explorer, HC-080, still shows the MOCKED BLOCKCHAIN fixtures).

## Responsibilities and owned concepts

- Hospital approval and registry. Hospital approval is served by the [hospital approval API](#hospital-approval-api-hc-131) (HC-131). The Federation Service's node registry ([`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml), HC-142) is only a routing directory: each registration cites a Governance approval decision, which it could now check with `getHospitalApproval`, but does not yet.
- Synchronization and research authorization. Synchronization requests, decisions, and the [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) check the Federation Service calls before every synchronization-decision query are served by the [synchronization request API](#synchronization-request-api-hc-132) (HC-132). Research access requests, decisions, and the [`research-authorization-check.v1.yaml`](../../contracts/api/research/research-authorization-check.v1.yaml) check the Research Service calls before each job are served by the [research access request API](#research-access-request-api-hc-133) (HC-133).
- Governance audit, served by the [governance audit API](#governance-audit-api-hc-134) (HC-134).
- Policy evaluation, served by the [governance policy engine](#governance-policy-engine-hc-135) (HC-135).
- Consent policy evaluation, served by [consent policy evaluation](#consent-policy-evaluation-hc-136) (HC-136): the Node evaluates grants held by the Hospital Nodes; it records none.
- OPTIONAL ledger adapter behind the application-owned [`AuditLedgerPort`](#audit-ledger-port-hc-190) (HC-190); only the [simulated immutable ledger](#simulated-immutable-ledger-hc-191) exists (HC-191, MOCKED), no blockchain adapter.

## Communication boundaries

The Node receives versioned requests and issues explicit decisions/authorization artifacts. Ledger access is an outbound adapter and contains minimized proofs only.

## Non-responsibilities

It does not own raw hospital clinical databases, clinician workflows, patient medical-record editing, company self-approval, or research notebook execution.

## Expected contracts

This Node provides [`hospital-approval.v1.yaml`](../../contracts/api/governance/hospital-approval.v1.yaml) (HC-131), [`synchronization-requests.v1.yaml`](../../contracts/api/governance/synchronization-requests.v1.yaml), and the Federation's [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) (HC-132), [`research-requests.v1.yaml`](../../contracts/api/governance/research-requests.v1.yaml), and the Research Service's [`research-authorization-check.v1.yaml`](../../contracts/api/research/research-authorization-check.v1.yaml) (HC-133), [`governance-audit-events.v1.yaml`](../../contracts/api/governance/governance-audit-events.v1.yaml) (HC-134), [`governance-policies.v1.yaml`](../../contracts/api/governance/governance-policies.v1.yaml) (HC-135), and [`governance-ledger-proofs.v1.yaml`](../../contracts/api/governance/governance-ledger-proofs.v1.yaml) (HC-191, simulated ledger). A consent contract remains PLANNED.
