# Governance Node

## Purpose and status

CONFIRMED Governance / Ethics Authority boundary. Its stack (Python + FastAPI, one process) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED at D2 (HC-130): a FastAPI app with Clean/Hexagonal layers, pinned dependencies, tests, and a liveness `GET /health`. The [hospital approval API](#hospital-approval-api-hc-131) is IMPLEMENTED at D2 (HC-131), over applications and decisions held **in memory**, seeded from fictional demo data: decisions are lost on restart, and the reviewer is declared, not authenticated. The [synchronization request API](#synchronization-request-api-hc-132) and the synchronization authorization check the Federation Service calls are IMPLEMENTED at D2 (HC-132), in memory the same way; patient grants are checked against fictional demo grants (**MOCKED**). The [research access request API](#research-access-request-api-hc-133) and the research authorization check the Research Service calls are IMPLEMENTED at D2 (HC-133), in memory the same way. The [governance audit API](#governance-audit-api-hc-134) is IMPLEMENTED at D2 (HC-134): the Node records the requests it receives, the decisions it records, and every authorization check it answers in its own minimized audit trail, in memory the same way. The [governance policy engine](#governance-policy-engine-hc-135) is IMPLEMENTED at D3 (HC-135): the Authority's review rules are a versioned, effective-dated policy, read from fictional data at startup; every review and decision applies the version in effect and every decision cites it. The policy is a fictional demo policy, not a validated legal or ethical framework, and new versions are published by editing the data and restarting. [Consent policy evaluation](#consent-policy-evaluation-hc-136) is IMPLEMENTED at D3 (HC-136): a synchronization's patient grant is evaluated against the grants of the Hospital Node holding it, over real HTTP, when reviewing and again before each exchange; a grant revoked there stops the authorization. The demo Hospital Nodes' grant stores are themselves MOCKED. The [`AuditLedgerPort`](#audit-ledger-port-hc-190) is defined (HC-190, D1) and the [simulated immutable ledger](#simulated-immutable-ledger-hc-191) behind it is IMPLEMENTED at D2 (HC-191): every decision recorded is anchored as a minimized proof, served by a read-only proofs API. [Ledger event hashing](#ledger-event-hashing-hc-192) is IMPLEMENTED at D2 (HC-192): each proof holds its payload's SHA-256 hash, the one the demo data's proofs use, and is served with the Node's verification of that hash against its audit trail. That default ledger is **MOCKED**: an append-only list in memory, not a blockchain. The [Besu permissioned ledger adapter](#besu-permissioned-ledger-hc-194) is IMPLEMENTED at D4 (HC-194, [ADR-0007](../../docs/decisions/ADR-0007-permissioned-audit-ledger.md)), opt-in: decisions are anchored in a Hyperledger Besu (QBFT) contract instead. It is tested against the compiled contract in an in-process EVM, but not VALIDATED against a running Besu node. [Authentication](#authentication-hc-211) is IMPLEMENTED at D2 (HC-211, [ADR-0010](../../docs/decisions/ADR-0010-authentication-foundation.md)), opt-in: with `GOVERNANCE_AUTH=required`, a person signs in with a password for a bearer session, and each decision needs the session of the reviewer it names. Off, the default, the reviewer stays declared. [Role-based access control](#role-based-access-control-hc-212) is IMPLEMENTED at D2 (HC-212, [ADR-0011](../../docs/decisions/ADR-0011-role-based-access-control.md)) on the same switch: every route but health, the published policies, and the service authorization checks needs a session whose role grants it, from a fixed fictional role matrix. [Organization identity](#organization-identity-hc-213) is IMPLEMENTED at D3 (HC-213, [ADR-0014](../../docs/decisions/ADR-0014-organization-identity.md)) on the same switch: a role counts only at a recognized organization that fits it, and a submission names the signed-in person's own organization. [Signed federation authorization](#signed-federation-authorization-hc-214) is IMPLEMENTED at D4 (HC-214, [ADR-0015](../../docs/decisions/ADR-0015-signed-federation-authorization.md)), opt-in: authorized synchronization checks carry an Ed25519-signed, five-minute statement of the exact exchange, which the target Hospital Node verifies on its own. [Security audit events](#security-audit-events-hc-215) (HC-215, D4) record sign-ins, refused sign-ins, and access denials on the authentication switch. Sessions are held in memory, for fictional demo people; the service authorization checks are not authenticated. There is no persistence. It is not deployed.

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

Decisions are anchored in the MOCKED simulated ledger by default. `GOVERNANCE_LEDGER=besu` anchors them on a Besu chain instead (see [Besu permissioned ledger](#besu-permissioned-ledger-hc-194)); any value other than `simulated` (default) or `besu` stops startup.

Decisions name a declared reviewer by default, and no caller is checked. `GOVERNANCE_AUTH=required` makes each decision need the reviewer's sign-in session, against the password hashes of `auth/.credentials.json` (see [Authentication](#authentication-hc-211)), and every other route but health, the policies, and the service checks need a session whose role grants it (see [Role-based access control](#role-based-access-control-hc-212)); any value other than `off` (default) or `required` stops startup.

Authorized synchronization checks are unsigned by default. `GOVERNANCE_FEDERATION_SIGNING=ed25519` signs each one with the private key of `GOVERNANCE_SIGNING_KEY` (default `auth/.signing-key.pem`, created by `python -m auth.create_signing_key`), for the target Hospital Node to verify (see [Signed federation authorization](#signed-federation-authorization-hc-214)); a missing or invalid key, or any value other than `off` (default) or `ed25519`, stops startup.

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
application/ledger.py                     # HC-190 AuditLedgerPort, anchoring and HC-192 verification use cases
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
adapters/outbound/besu_audit_ledger.py                # HC-194 Besu (QBFT) ledger, opt-in (ADR-0007)
domain/authentication.py, application/authentication.py   # HC-211 sessions, throttling, sign-in use cases
adapters/inbound/http/authentication.py               # HC-211 sign-in routes; HC-212 AccessControl, each route's check
domain/access_control.py, application/access_control.py  # HC-212 role matrix and authorize use case
domain/organization_identity.py                       # HC-213 affiliation and acting-for rules
adapters/outbound/fixture_organization_directory.py   # HC-213 the organizations the Node knows (fictional)
adapters/outbound/scrypt_password_hasher.py           # HC-211 password hashes (stdlib scrypt)
adapters/outbound/credential_file.py                  # HC-211 credentials, from auth/.credentials.json
adapters/outbound/in_memory_sessions.py               # HC-211 sessions, in memory
auth/set_password.py                                  # HC-211 writes a person's password hash
domain/federation_authorization.py                    # HC-214 what an authorized check attests
application/federation_authorization.py               # HC-214 AuthorizationSigner port, signing use case
adapters/outbound/ed25519_authorization_signer.py     # HC-214 Ed25519 compact JWS (ADR-0015)
auth/create_signing_key.py                            # HC-214 writes the signing key pair
ledger/AuditAnchor.sol, AuditAnchor.json              # HC-194 anchoring contract and its compiled artifact
ledger/compile_contract.py                            # recompiles the artifact after a contract change
ledger/qbft-config.json, dev_chain.py                 # local single-validator Besu chain (not yet run)
tests/                                    # domain, use case, adapter, HTTP, and layer-boundary tests
```

`GET /health` is a liveness check only:

```json
{
  "status": "ok",
  "node": "governance-node",
  "version": "0.9.0",
  "node_ref": "node-governance",
  "organization_ref": "org-governance",
  "capabilities": ["hospital_approval", "synchronization", "research", "audit", "policy", "ledger"],
  "grants": "http",
  "authentication": "off",
  "notice": "Governance Node (HC-130 to HC-136, HC-191, HC-192, HC-211). ... Liveness only; not a production health check."
}
```

`capabilities` lists the governance APIs served. `authentication` is `off` or `required` ([HC-211](#authentication-hc-211)). Every route not documented here answers `404`. A test checks the exact set of routes served, so each new route must come with its ticket.

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

**Storage and identity, at D2:** `InMemoryHospitalApplicationStore` holds the applications and decisions. At startup it loads the hospital applications and their decisions from the fictional [`demo-data/governance.json`](../../demo-data/governance.json), and checks that each decided application cites its own decision with the same outcome. Decisions recorded through the API stay in memory and are **lost on restart**; persistence is OPEN. `FixtureReviewerDirectory` reads the staff and clinicians of the fictional [`demo-data/people.json`](../../demo-data/people.json), never patients or relatives. By default the reviewer is **declared by the caller, not authenticated**: anyone who can reach the Node can claim to be `usr-olfa`. With [authentication required](#authentication-hc-211) (HC-211), a decision needs the reviewer's own bearer session. Either way this is demo-depth behavior, not production security.

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
- `submitted_by_ref` and `reviewer_ref` are declared by the caller, **not authenticated**, unless [authentication is required](#authentication-hc-211): then each must be the signed-in person (HC-211, HC-212), and `requester_organization_ref` their organization (HC-213).

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

**Storage, at D2:** `InMemoryResearchStore` holds requests and decisions, seeded from the fictional [`demo-data/governance.json`](../../demo-data/governance.json) (requests and decisions, with the structured `researchAuthorization` of `dec-rar-001`) and `research.json` (each request's project content). Everything recorded through the API is **lost on restart**, and `submitted_by_ref` and `reviewer_ref` are declared, **not authenticated**, unless [authentication is required](#authentication-hc-211): then each must be the signed-in person (HC-211, HC-212), and `research_organization_ref` their organization (HC-213).

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

IMPLEMENTED at D1, as a boundary. [`application/ledger.py`](application/ledger.py) owns the OPTIONAL `AuditLedgerPort` through which a ledger adapter anchors governance proofs. Two adapters implement it: the [simulated immutable ledger](#simulated-immutable-ledger-hc-191) (HC-191, MOCKED, default) and the [Besu permissioned ledger](#besu-permissioned-ledger-hc-194) (HC-194, opt-in).

**What may be anchored** ([`domain/ledger.py`](domain/ledger.py)): `proof_payload` turns a `decision_recorded` audit event into a `ProofPayload` of six fields only: the event reference, the decision reference, the outcome, the time decided, the organizations (the Authority first), and the payload version (`1`). These are the fields the demo ledger proofs of [`demo-data/governance.json`](../../demo-data/governance.json) anchor, and the seed events `evt-003` and `evt-004` give exactly those payloads. The actor is not anchored. The type has no field for a patient reference, a purpose, a rationale, a data scope, or clinical content, so none can reach a ledger through it. Requests received and authorization checks are not anchorable (`NotAnchorable`).

| Port member | Contract |
|---|---|
| `anchor(payload) -> LedgerProof` | Anchors append-only and returns the receipt: proof reference, payload, ledger name, time anchored, and the payload's hash (HC-192). Raises `LedgerUnavailable` when nothing was anchored. |
| `proof(event_ref) -> LedgerProof \| None` | The proof anchoring an event, if any. Raises `LedgerUnavailable`. |
| `proofs() -> list[LedgerProof]` | Every proof, in the order anchored (added by HC-191 to serve them). Raises `LedgerUnavailable`. |
| `simulated` | Whether proofs are held by a simulation rather than a real ledger, so a simulation is never shown as a real ledger. |

**Use cases:** `anchor_decision` anchors a recorded decision once: anchoring it again returns its proof, and the same event with another payload is a `ProofConflict`. `anchor_recorded` is what the decision use cases call after recording a decision (HC-191): the decision stands whatever happens, and a ledger that is unavailable leaves it unanchored. `get_proof` raises `ProofNotFound` for an event without proof; `list_proofs` lists them, the latest anchored first. They are tested against a test double that stays in `tests/` (`test_ledger.py`, `test_ledger_use_cases.py`); the layer test keeps any ledger library out of `domain/` and `application/`.

Not done: signatures beyond the Besu ledger's transactions.

## Simulated immutable ledger (HC-191)

IMPLEMENTED at D2, **MOCKED**. [`adapters/outbound/simulated_audit_ledger.py`](adapters/outbound/simulated_audit_ledger.py) implements the `AuditLedgerPort` as an append-only list in this process's memory, named `local-simulation`, with `simulated: true`. It is **not a blockchain and not a real ledger**: no consensus, signature, replication, or durability; the payload hash (HC-192) is computed by the Node itself. Proofs anchored at runtime are **lost on restart**. "Immutable" means only that nothing changes or removes a proof once anchored: an event is anchored once, the same payload again returns the same proof, and another payload for the same event is refused (`ProofConflict`), even under concurrent calls.

**Anchoring.** Each hospital approval, synchronization, or research decision recorded through the APIs (HC-131 to HC-133) is stored, recorded in the audit trail as `decision_recorded`, and then anchored: its [six-field minimized payload](#audit-ledger-port-hc-190) becomes the next `proof-NNN`, at the Node's clock time. A refused decision (`403`, `409`, `422`) records nothing, so it anchors nothing. Requests received and authorization checks are never anchored. The decision stands whether or not it was anchored; an unanchored decision is not retried (OPEN). The simulated ledger is always available, so at D2 this never happens.

**Seed.** At startup the ledger loads the two fictional simulated proofs of [`demo-data/governance.json`](../../demo-data/governance.json) (`proof-003` for `evt-003`, `proof-004` for `evt-004`). Each must be marked simulated in `local-simulation`, anchor exactly the six payload fields, and match the payload of the seed audit event it names; and, since HC-192, hold the SHA-256 hash of that payload (`hashAlgorithm`, `hash`); otherwise startup stops. The seed decisions `evt-001`, `evt-002`, and `evt-005` have no proof in the demo data and stay unanchored.

| Route | Contract | Purpose |
|---|---|---|
| `GET /v1/ledger/proofs` | [`governance-ledger-proofs.v1.yaml`](../../contracts/api/governance/governance-ledger-proofs.v1.yaml) | Every proof, the latest anchored first, with `simulated` and a MOCKED BLOCKCHAIN notice. |
| `GET /v1/audit/events/{event_ref}/proof` | same | The proof anchoring one audit event. `404 event_not_found` for an unknown event; `404 proof_not_found` for an event without proof. |

Either route answers `503 ledger_unavailable` if the ledger cannot be read; the simulated ledger always can. A proof carries the proof reference, the ledger name, the time anchored, the [payload hash and its verification](#ledger-event-hashing-hc-192), and the payload, never the actor, a patient reference, a purpose, a rationale, a scope, or clinical content. Readers are not authenticated.

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

Not done at D2 in this adapter: signatures, durability (see the [Besu ledger](#besu-permissioned-ledger-hc-194) for both), retrying an unanchored decision, anchoring the policy version, and the Governance Portal reading these proofs (its proof explorer, HC-080, still shows the MOCKED BLOCKCHAIN fixtures).

## Ledger event hashing (HC-192)

IMPLEMENTED at D2. Each proof holds the SHA-256 hash of its [six-field payload](#audit-ledger-port-hc-190), so a change to an anchored payload, or to the audit event it anchors, is evident. It is not a signature: it proves no author, and the hash is computed and held by the same Node, in the same **MOCKED** simulated ledger, anchored nowhere else.

**Canonical form** ([`domain/ledger.py`](domain/ledger.py), `canonical_payload` and `hash_payload`): the payload as a JSON object with the field names of the demo proofs' `anchoredPayload` (`eventId`, `decisionId`, `outcome`, `decidedAt`, `organizationIds`, `version`), keys sorted, no whitespace, non-ASCII characters unescaped, encoded as UTF-8, `decidedAt` in ISO 8601 with its offset as served. This is the hash [`demo-data/check_fixtures.py`](../../demo-data/check_fixtures.py) checks: the seed events `evt-003` and `evt-004` hash to the fixtures' `hash`, and a test pins the two implementations together, non-ASCII included.

**Anchoring.** The simulated ledger hashes each payload it anchors; the seed proofs must already hold their payload's hash (see [Seed](#simulated-immutable-ledger-hc-191)).

**Verification** (`domain.ledger.verify`, `application.ledger.verify_proof`): whenever a proof is served, the Node recomputes the hash of the proof's payload and of the payload of the audit event it anchors, as the trail holds it now, and answers, in the states of the portal's proof explorer (HC-080):

| `verification` | When |
|---|---|
| `verified` | The hash is the payload's, and the audit event still gives that payload. |
| `tampered` | The hash differs from the payload's, or from the audit event's payload, or the algorithm is not SHA-256. |
| `inconsistent` | The audit event is missing or is not a recorded decision. |

The proofs API (contract 1.1.0) serves `hash_algorithm`, `payload_hash`, and `verification` with each proof. At D2 every proof the Node serves is `verified`: its trail and ledger are both in its own memory and immutable there; `tampered` and `inconsistent` are shown by tests with a forged proof or a changed event. This is a self-check by the Node that holds the proofs, not an independent verification; anyone can re-hash the served payload instead.

```bash
# proof-005 for evt-008, after approving sync-001: verification "verified" and
# payload_hash 44556e2c...ad8df, the SHA-256 of its canonical payload.
curl -s localhost:8200/v1/audit/events/evt-008/proof
```

Not done at D2: signatures, hash chaining between proofs, and the Governance Portal reading these hashes (its proof explorer, HC-080, re-hashes the fixtures in the browser and escapes non-ASCII characters, unlike this form; they agree on the ASCII-only demo data).

## Besu permissioned ledger (HC-194)

IMPLEMENTED at D4, opt-in, **not VALIDATED against a running Besu node**. [ADR-0007](../../docs/decisions/ADR-0007-permissioned-audit-ledger.md) records the decision: trust model B (validators co-operated by independent organizations, as a target) and Hyperledger Besu with QBFT. [`adapters/outbound/besu_audit_ledger.py`](adapters/outbound/besu_audit_ledger.py) implements the unchanged `AuditLedgerPort` with `web3`, with `simulated: false`.

**Contract** ([`ledger/AuditAnchor.sol`](ledger/AuditAnchor.sol)): append-only. `anchor(eventRef, payload)` is accepted only from the account that deployed the contract (the Governance Node's ledger account) and only once per event. The contract computes the payload's SHA-256 and keeps the payload, the hash, and the block time. The payload is the [six-field canonical form](#ledger-event-hashing-hc-192), so a reader of the chain can recompute the hash without the Node. Nothing else is anchored: no actor, patient reference, purpose, rationale, scope, or clinical content. [`ledger/AuditAnchor.json`](ledger/AuditAnchor.json) is the committed compiled artifact (solc 0.8.26, EVM Berlin). It records its source's SHA-256, which a test compares with the source. Recompile it with [`ledger/compile_contract.py`](ledger/compile_contract.py) after changing the contract.

**Anchoring.** As with the simulated ledger, each decision recorded is anchored at once by `anchor_recorded`. The adapter signs a transaction with the ledger account's key and waits for its block, for up to 15 seconds. It then reads the proof back from the chain. The proof's `ledger` is `besu-qbft:<contract address>`, its `proof_ref` is `<contract address>:<position>`, its `anchored_at` is the block time in UTC, and its `payload_hash` is the one the chain computed. The same payload again returns the same proof. Another payload for an event already anchored is a `ProofConflict`, so the decision stands unanchored. An unreachable node, a timeout, or a refused transaction (for example, a contract owned by another account) is `LedgerUnavailable`: the decision stands unanchored at once, because the client does not retry. Reading proofs then answers `503 ledger_unavailable`. The proofs API serves `simulated: false` and a notice saying the ledger is independent of the Governance Node only if other organizations run its validators.

**Configuration** (environment):

| Variable | Meaning |
|---|---|
| `GOVERNANCE_LEDGER` | `besu` to use this adapter; `simulated` by default. |
| `GOVERNANCE_LEDGER_RPC_URL` | The Besu node's JSON-RPC, `http://127.0.0.1:8545` by default. |
| `GOVERNANCE_LEDGER_KEY_FILE` | Required: a file holding the ledger account's private key (hex). Never commit it. |
| `GOVERNANCE_LEDGER_CONTRACT` | Optional: an `AuditAnchor` contract already deployed by that account. If it is not set, the Node deploys a new contract at startup, so its proofs start empty, like its in-memory audit trail; earlier contracts stay on the chain, unread. |

A missing key file, or a failed deployment, stops startup. The simulated seed proofs are not on the chain, so the seed decisions have no proof there (`404 proof_not_found`).

**Local chain** ([`ledger/dev_chain.py`](ledger/dev_chain.py), **not yet run**): with the Besu distribution (26.x, Java 21) on PATH, `python ledger/dev_chain.py` generates, on first run, a ledger account key and a single-validator QBFT genesis from [`ledger/qbft-config.json`](ledger/qbft-config.json) into the gitignored `ledger/.chain/`. It then serves JSON-RPC on `127.0.0.1:8545`, with zero gas price and peer-to-peer off. Then:

```bash
GOVERNANCE_GRANTS=fixture GOVERNANCE_LEDGER=besu \
  GOVERNANCE_LEDGER_KEY_FILE=ledger/.chain/anchor.key python main.py
# Approve sync-001 as in the synchronization demo, then:
curl -s localhost:8200/v1/audit/events/evt-008/proof   # simulated: false, besu-qbft:0x...
```

**Tests.** [`tests/test_besu_audit_ledger.py`](tests/test_besu_audit_ledger.py) runs the adapter and the compiled contract in py-evm through eth-tester, an in-process EVM: anchoring, reading back, conflicts, order, a contract owned by another account, an unreachable node, startup errors, and a decision recorded through the API, checked against the contract's `anchoredOnBesu` example. This checks the adapter and the contract, not Besu's consensus, RPC, or genesis. `test_live_besu_deploys_anchors_and_reads_back` runs against a real chain when `GOVERNANCE_LEDGER_LIVE_RPC` and `GOVERNANCE_LEDGER_LIVE_KEY_FILE` are set; it has not been run.

Not done at D4: validation against a running Besu node; validators run by other organizations (the demo chain has one validator, run locally, so it gives **no assurance independent of the Governance Node**); validator onboarding and node permissioning; key management beyond a local file; asynchronous anchoring and retry; who may read the chain; and the Governance Portal reading these proofs.

## Authentication (HC-211)

IMPLEMENTED at D2, opt-in. [ADR-0010](../../docs/decisions/ADR-0010-authentication-foundation.md) records the decision: each runtime authenticates the people who act on it, from its own credentials, with no central identity provider. This Node serves [`authentication.v1.yaml`](../../contracts/api/auth/authentication.v1.yaml) when started with `GOVERNANCE_AUTH=required`; off (the default), it serves no sign-in route and its decisions keep the declared `reviewer_ref`.

| Route | Purpose |
|---|---|
| `POST /v1/auth/sessions` | Sign in with `person_ref` and `password`. `201` with a `session_token` (shown once), the person's role, organization, and `permissions` (HC-212), and `expires_at`; `401 authentication_failed` otherwise. |
| `GET /v1/auth/session` | Who the bearer session belongs to, what their role grants, and until when; never the token. |
| `DELETE /v1/auth/session` | Sign out. `204`. |

**Decisions.** With authentication required, the three decision routes (hospital applications, synchronization requests, research requests) check the session first: none, an unknown one, or an expired one is `401 authentication_required`, with a `WWW-Authenticate: Bearer` challenge. Then a `reviewer_ref` that is not the signed-in person is `403 reviewer_mismatch`. The review rules apply after that, unchanged. Since HC-212, a signed-in person whose role does not grant `governance:review` is refused before that, `403 permission_denied`, and reads and submissions need a session too: see [Role-based access control](#role-based-access-control-hc-212). The Federation and Research Services' authorization checks are not authenticated.

**Credentials.** `python -m auth.set_password usr-olfa` asks for a password (at least 12 characters) twice and writes only its salted scrypt hash (n=2^15, r=8, p=3) to `auth/.credentials.json`, gitignored; `GOVERNANCE_CREDENTIALS` names another file. Only staff and clinicians of [`demo-data/people.json`](../../demo-data/people.json) can have one. A missing or malformed file, an unknown person, or a hash that is not scrypt stops startup. The credentials of this demo belong to fictional people and are created on each machine: nothing is committed.

**Sessions and failures.** A session token is random (256 bits), and the Node keeps only its SHA-256 digest. A session lasts 8 hours, with no renewal, and ends on sign-out. Unknown person, wrong password, and an account locked after 5 failures in a row (for 15 minutes) all answer the same `401`, after the same scrypt verification. Sessions and failure counts are held **in memory**: a restart signs everyone out and unlocks every account.

Demo, from this directory:

```bash
python -m auth.set_password usr-olfa            # choose a password
GOVERNANCE_AUTH=required GOVERNANCE_GRANTS=fixture python main.py

# A decision without a session: 401 authentication_required.
BODY='{"reviewer_ref":"usr-olfa","outcome":"approved","rationale":"Finalité de soins, périmètre limité, autorisation du patient active.","conditions":[],"approved_days":13,"manual_checks_confirmed":false}'
curl -s -X POST localhost:8200/v1/synchronization-requests/sync-001/decision \
  -H 'content-type: application/json' -d "$BODY"

# Sign in, then decide with the session: 201, decided_by_ref usr-olfa. Then sign out.
TOKEN=$(curl -s -X POST localhost:8200/v1/auth/sessions -H 'content-type: application/json' \
  -d '{"person_ref":"usr-olfa","password":"<your password>"}' \
  | python -c "import json, sys; print(json.load(sys.stdin)['session_token'])")
curl -s -X POST localhost:8200/v1/synchronization-requests/sync-001/decision \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d "$BODY"
curl -s -X DELETE localhost:8200/v1/auth/session -H "Authorization: Bearer $TOKEN"
```

**Tests:** domain rules (`test_authentication.py`), use cases with test doubles (`test_authentication_use_cases.py`), the hasher and credential file (`test_password_credentials.py`), the environment switch (`test_auth_mode.py`), and HTTP against the authentication contract and the three decision contracts (`test_authentication_http.py`). The flow was also run over HTTP against a running Node.

Not done at D2: an OIDC provider or federation with organizations' identity providers; MFA; password reset and account administration; persistence of sessions (sign-ins are audited since [HC-215](#security-audit-events-hc-215)); service-to-service authentication (HC-214); and the Governance Portal signing in to this Node (it still uses HC-210's demo personas, MOCKED). This is not production identity.

## Role-based access control (HC-212)

IMPLEMENTED at D2, on the same opt-in switch as [authentication](#authentication-hc-211). [ADR-0011](../../docs/decisions/ADR-0011-role-based-access-control.md) records the decision: a fixed role-to-permission matrix in the Node's domain ([`domain/access_control.py`](domain/access_control.py)), deny by default, checked on every protected route at every call.

| Role (demo data) | Permissions | So it may |
|---|---|---|
| `governance_reviewer` (`usr-olfa`) | `governance:review`, `governance:audit` | read and decide hospital applications, synchronization and research requests; read the audit trail and ledger proofs |
| `hospital_manager` (`usr-mehdi`), `physician` (`clin-ines`, …) | `synchronization:request` | submit a synchronization request |
| `researcher` (`usr-aymen`) | `research:request` | submit a research access request |
| `nurse`, and any other role | none | nothing here |

With `GOVERNANCE_AUTH=required`, each protected route checks, in order: a valid session (`401 authentication_required`); the person's role grants the route's permission (`403 permission_denied`, before anything is looked up, so a role without it cannot learn which records exist); then, for submissions and decisions, that `submitted_by_ref` or `reviewer_ref` is the signed-in person (`403 submitter_mismatch`, `403 reviewer_mismatch`). The domain's review rules read the same matrix: only a role granting `governance:review` may decide, with authentication off too. `GET /health`, the published policies, sign-in, and the Federation and Research Services' authorization checks stay open (service authentication is HC-214). The sign-in and session responses list the person's `permissions` (`authentication.v1.yaml` 1.1.0), for display only. Off, the default, nothing is checked.

Contracts: the hospital approval (1.3.0), synchronization requests (1.4.0), research requests (1.3.0), audit events (1.1.0), and ledger proofs (1.3.0) contracts declare the optional bearer session, `401`, and `403 permission_denied` on each protected operation.

Demo, from this directory, after `python -m auth.set_password` for `usr-olfa` and `usr-aymen`:

```bash
GOVERNANCE_AUTH=required GOVERNANCE_GRANTS=fixture python main.py

tok() { curl -s -X POST localhost:8200/v1/auth/sessions -H 'content-type: application/json' \
  -d "{\"person_ref\":\"$1\",\"password\":\"$2\"}" \
  | python -c "import json, sys; print(json.load(sys.stdin)['session_token'])"; }
OLFA=$(tok usr-olfa '<her password>'); AYMEN=$(tok usr-aymen '<his password>')

curl -s localhost:8200/v1/audit/events                                   # 401 authentication_required
curl -s localhost:8200/v1/audit/events -H "Authorization: Bearer $AYMEN" # 403 permission_denied
curl -s localhost:8200/v1/audit/events -H "Authorization: Bearer $OLFA"  # 200
curl -s localhost:8200/v1/auth/session -H "Authorization: Bearer $AYMEN" # permissions: ["research:request"]
```

**Tests:** the matrix and the `authorize` use case (`test_access_control.py`), and over HTTP every protected route against its contract, without a session, with a role that does not grant it, with one that does, and with authentication off (`test_access_control_http.py`). These scenarios, and a physician's synchronization request (`201`), a hospital manager's submitted as someone else (`403 submitter_mismatch`), and a physician's decision (`403 permission_denied`), were also run over HTTP against a running Node.

Not done at D2: service authentication (still OPEN; HC-214 signs authorizations, not callers); more than one role per person; editing the matrix without code; and the Governance Portal using these permissions (it still uses HC-210's browser-side scopes, MOCKED). The matrix is fictional demo policy, not a validated access policy, and this is not production security.

## Organization identity (HC-213)

IMPLEMENTED at D3, on the same opt-in switch as [authentication](#authentication-hc-211). [ADR-0014](../../docs/decisions/ADR-0014-organization-identity.md) records the decision. The Node knows the organizations it governs, with their type, from the fictional [`demo-data/organizations.json`](../../demo-data/organizations.json), read once at startup behind an `OrganizationDirectory` port ([`adapters/outbound/fixture_organization_directory.py`](adapters/outbound/fixture_organization_directory.py)); an unknown type stops startup. [`domain/organization_identity.py`](domain/organization_identity.py) holds two rules:

- **A role counts only at an organization that fits it.** `governance_reviewer` at the `governance_authority` this Node runs for (its `NodeIdentity`, `org-governance` in the demo), never a hospital or the platform company; `hospital_manager` and `physician` at a `hospital` or `private_practice`; `researcher` at a `research_institution`. Checked on every protected route after the role (`403 permission_denied`, with the reason in `detail`).
- **A person acts only for their own organization.** A synchronization request's `requester_organization_ref` and a research request's `research_organization_ref` must be the signed-in person's organization: `403 organization_mismatch`, after `submitter_mismatch`, and nothing is recorded.

Governance reviewers still read every organization's applications and requests: reviewing them is the Authority's role, and the conflict-of-interest rules still forbid deciding on one's own organization. Off, the default, declared organizations are trusted. Whether a hospital is approved still comes from the Authority's decisions (HC-131), not from the organizations file.

Contracts: synchronization requests 1.5.0 and research requests 1.4.0 add `403 organization_mismatch`; hospital approval 1.3.1, audit events 1.1.1, and ledger proofs 1.3.1 note the reviewer case (wording only).

Demo, with `tok` as for [role-based access control](#role-based-access-control-hc-212), after `python -m auth.set_password` for `usr-mehdi` (hospital manager of Hospital C):

```bash
MEHDI=$(tok usr-mehdi '<his password>')
sync() { curl -s -X POST localhost:8200/v1/synchronization-requests \
  -H "Authorization: Bearer $MEHDI" -H 'content-type: application/json' \
  -d "{\"requester_organization_ref\":\"$1\",\"submitted_by_ref\":\"usr-mehdi\",
       \"target_organization_ref\":\"org-hospital-a\",\"patient_ref\":\"pat-b\",
       \"purpose\":\"Suivi\",\"scope\":[\"lab_reports\"],\"duration_days\":30,
       \"consent\":{\"basis\":\"none\",\"access_grant_ref\":null}}"; }
sync org-hospital-b   # 403 organization_mismatch: usr-mehdi does not speak for Hospital B
sync org-hospital-c   # 201, requested by Hospital C
```

**Tests:** the affiliation and acting-for rules and the fixture directory, including every demo staff member and clinician being recognized (`test_organization_identity.py`); the `authorize` use case with an unrecognized organization (`test_access_control.py`); and over HTTP against the contracts, a submission for another organization, one for one's own, nothing recorded on refusal, a reviewer of another Authority refused on every reviewer route, and authentication off (`test_organization_identity_http.py`). These scenarios were also run over HTTP against a running Node.

Not done at D3: federating each organization's own identity provider; verifying institutions cryptographically (HC-214 signs the Authority's federation authorizations, not people's affiliations); more than one affiliation per person; checking a research request's principal investigator against its organization; letting requesters read their own organization's requests. Denials are audited since [HC-215](#security-audit-events-hc-215). Organizations and affiliations are fictional demo data, not a verified institution registry, and this is not production security.

## Signed federation authorization (HC-214)

IMPLEMENTED at D4, opt-in, not VALIDATED by a security review. [ADR-0015](../../docs/decisions/ADR-0015-signed-federation-authorization.md) records the decision. With `GOVERNANCE_FEDERATION_SIGNING=ed25519`, every `authorized` answer of the [Federation Service's check](#synchronization-request-api-hc-132) carries `signed_authorization` ([`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) 1.2.0): a compact JWS signed with Ed25519, which the Federation Service passes on unchanged and the target Hospital Node verifies on its own with this Node's public key ([Hospital Node](../hospital-node/README.md#signed-synchronization-authorizations-hc-214)).

- **What it attests** ([`domain/federation_authorization.py`](domain/federation_authorization.py)): this Authority (`iss`), the decision (`sub`), the target organizations (`aud`), and the exchange exactly as asked: requester organization, actor, patient, scope as asked (never the wider approved scope), and purpose; with a unique `jti`.
- **For five minutes at most:** it expires at the earlier of the decision's `valid_until` and five minutes after the check, so an expired decision or a withdrawn patient grant ([HC-136](#consent-policy-evaluation-hc-136)) stops the exchange within five minutes.
- **Only what is authorized:** a denial, a `503`, or a Node with signing off answers `signed_authorization: null`. Each check is audited as before; the token is not stored.
- **Keys:** `python -m auth.create_signing_key` writes a new private key to `auth/.signing-key.pem` (gitignored; or `GOVERNANCE_SIGNING_KEY`) and its public key to `auth/.signing-key.pub.pem`, and prints the key id (RFC 7638 thumbprint, the token's `kid`). It never replaces an existing key. Give the public key to each Hospital Node out of band; to rotate, delete the key, create a new one, and redistribute the public key. `/health` reports `federation_signing` (`off` or `ed25519`).

Demo, with Hospital B verifying ([its signed configuration](../hospital-node/config/hospital-b.signed-authorization.json) reads the public key from this folder) and the Federation Service on `8300`:

```bash
python -m auth.create_signing_key
GOVERNANCE_FEDERATION_SIGNING=ed25519 python main.py
# Hospital B:  HOSPITAL_NODE_CONFIG=config/hospital-b.signed-authorization.json python main.py
# Federation:  FEDERATION_REGISTRY_SEED=registry-seed.demo.json fastapi run main.py --port 8300
# Demo step 20: approve sync-001 as in the synchronization demo above, then:
curl -s -X POST localhost:8300/v1/federated-queries -H 'content-type: application/json' -d '{
  "patient_ref": "pat-a", "scope": ["medications"],
  "purpose": "Continuité des soins : consultation de cardiologie",
  "requested_by": {"organization_ref": "org-hospital-a", "actor_ref": "clin-x"},
  "authorization": {"basis": "synchronization_decision", "ref": "dec-sync-001",
                    "expires_at": "<valid_until of the decision>"}}'
```

Hospital B answers `ok` with `med-b-leila-coagulix`: it knows `dec-sync-001` only from the signed authorization, since the decision exists only in this Node's memory. Restarted without `GOVERNANCE_FEDERATION_SIGNING`, the same query is `denied` by Hospital B. Sent to Hospital B directly, without the token, with a changed claim, or for another patient or a wider scope, it is `403`.

**Tests:** the attested claims, scope, and lifetime, and nothing attested for a denial (`test_federation_authorization.py`); the Ed25519 adapter against the RFC 8037 thumbprint example, a changed claim or another key failing verification, and invalid keys stopping startup (same file); and over HTTP against the contract, a signed authorized answer verifiable with the public key, one token per check, `null` for denials and with signing off, `/health`, and the startup switch (`test_federation_authorization_http.py`). The demo above was run against running Governance, Hospital B, and Federation processes, with both signing modes.

Not done at D4: authentication of the services calling the check; replay detection and revocation of an issued token before it expires; key rotation with more than one trusted key, key custody beyond a file, and publishing the key; signing research authorizations (HC-133). Transport is plain HTTP in the demo. This is not production security; the [HC-215 threat model](../../docs/security/threat-model.md) lists these as findings F-02, F-03, F-07, and F-09.

## Security audit events (HC-215)

IMPLEMENTED at D4, on the same opt-in switch as [authentication](#authentication-hc-211); part of the [security audit and threat model](../../docs/security/threat-model.md). With `GOVERNANCE_AUTH=required`, the Node records in its own [audit trail](#governance-audit-api-hc-134) ([`governance-audit-events.v1.yaml`](../../contracts/api/governance/governance-audit-events.v1.yaml) 1.2.0), in domain `security`:

- `signed_in`: a session issued, recorded before the token is returned (subject `person`).
- `sign_in_refused`: a wrong password for a known account that is not locked, reason `invalid_credentials`, or `account_locked` for the failure that locks it (subject `person`).
- `access_denied`: a signed-in person answered `403` on a protected route, subject `permission` (the route's permission), reason `permission_denied`, `reviewer_mismatch`, `submitter_mismatch`, or `organization_mismatch`.

Events are minimized like the others: never a password, a token, a header, or the request's content. To keep the trail bounded, refusals for an unknown person, attempts on a locked account, and requests without a valid session (`401`) are not recorded; the lockout caps the recorded refusals at five per account per 15 minutes. With authentication off, nothing is recorded in this domain. The rules are in [`domain/audit.py`](domain/audit.py); the `sign_in` and `authorize` use cases and `record_denial` ([`application/`](application/)) record them.

```bash
GOVERNANCE_AUTH=required python main.py
# a wrong password for usr-olfa, then usr-olfa and usr-aymen sign in, and usr-aymen reads the trail (403);
curl -s 'localhost:8200/v1/audit/events?domain=security' -H "Authorization: Bearer $OLFA"
# access_denied (usr-aymen, governance:audit, permission_denied), signed_in x2, sign_in_refused (invalid_credentials)
```

**Tests:** the event rules (`test_audit.py`); the use cases with test doubles, including the lockout and unknown-person bounds (`test_authentication_use_cases.py`, `test_access_control.py`); and over HTTP against the contract, its `security` example reproduced exactly, each mismatch, no event for `401`, one `account_locked` per lockout, and nothing with authentication off (`test_security_audit_http.py`). The demo above was run against a running Node.

Not done at D4: a durable trail and retention; alerting on `account_locked`; per-client throttling. The trail is in memory, and this is not production audit.

## Responsibilities and owned concepts

- Hospital approval and registry. Hospital approval is served by the [hospital approval API](#hospital-approval-api-hc-131) (HC-131). The Federation Service's node registry ([`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml), HC-142) is only a routing directory: each registration cites a Governance approval decision, which it could now check with `getHospitalApproval`, but does not yet.
- Synchronization and research authorization. Synchronization requests, decisions, and the [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) check the Federation Service calls before every synchronization-decision query are served by the [synchronization request API](#synchronization-request-api-hc-132) (HC-132). Research access requests, decisions, and the [`research-authorization-check.v1.yaml`](../../contracts/api/research/research-authorization-check.v1.yaml) check the Research Service calls before each job are served by the [research access request API](#research-access-request-api-hc-133) (HC-133).
- Governance audit, served by the [governance audit API](#governance-audit-api-hc-134) (HC-134).
- Policy evaluation, served by the [governance policy engine](#governance-policy-engine-hc-135) (HC-135).
- Consent policy evaluation, served by [consent policy evaluation](#consent-policy-evaluation-hc-136) (HC-136): the Node evaluates grants held by the Hospital Nodes; it records none.
- Authentication of the people who act here, served by [authentication](#authentication-hc-211) (HC-211, opt-in), from its own credentials, and what each may do, by [role-based access control](#role-based-access-control-hc-212) (HC-212, opt-in).
- OPTIONAL ledger adapters behind the application-owned [`AuditLedgerPort`](#audit-ledger-port-hc-190) (HC-190): the [simulated immutable ledger](#simulated-immutable-ledger-hc-191) (HC-191, MOCKED, default) and the [Besu permissioned ledger](#besu-permissioned-ledger-hc-194) (HC-194, opt-in, not VALIDATED against a running node).

## Communication boundaries

The Node receives versioned requests and issues explicit decisions/authorization artifacts. Ledger access is an outbound adapter and contains minimized proofs only.

## Non-responsibilities

It does not own raw hospital clinical databases, clinician workflows, patient medical-record editing, company self-approval, or research notebook execution.

## Expected contracts

This Node provides [`hospital-approval.v1.yaml`](../../contracts/api/governance/hospital-approval.v1.yaml) (HC-131), [`synchronization-requests.v1.yaml`](../../contracts/api/governance/synchronization-requests.v1.yaml), and the Federation's [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) (HC-132), [`research-requests.v1.yaml`](../../contracts/api/governance/research-requests.v1.yaml), and the Research Service's [`research-authorization-check.v1.yaml`](../../contracts/api/research/research-authorization-check.v1.yaml) (HC-133), [`governance-audit-events.v1.yaml`](../../contracts/api/governance/governance-audit-events.v1.yaml) (HC-134), [`governance-policies.v1.yaml`](../../contracts/api/governance/governance-policies.v1.yaml) (HC-135), [`governance-ledger-proofs.v1.yaml`](../../contracts/api/governance/governance-ledger-proofs.v1.yaml) (HC-191, simulated ledger), and [`authentication.v1.yaml`](../../contracts/api/auth/authentication.v1.yaml) (HC-211, when authentication is required). A consent contract remains PLANNED.
