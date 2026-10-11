# Hospital Node

## Purpose and status

CONFIRMED autonomous hospital-controlled boundary. Its stack (Python + FastAPI, one process per hospital from one codebase, flat layer layout that keeps `adapters/dmi/`) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-110): a FastAPI app with Clean/Hexagonal layers, pinned dependencies, and tests. Per-hospital configuration loading is IMPLEMENTED at D2 (HC-112). Its clinical repository is **MOCKED** at D2 (HC-113): fictional demo records, read-only, in memory. It serves `GET /health` (HC-111, IMPLEMENTED at D2) and the [patient history API](#patient-history-api-hc-114) (HC-114, IMPLEMENTED at D2): its side of the Federation contract, whose authorization check is **MOCKED** against fictional grants and decisions. Every query it answers or refuses is recorded in its own [audit trail](#audit-event-api-hc-116) (HC-116, IMPLEMENTED at D2), kept **in memory only** and readable through an unauthenticated API. The [access grants API](#access-grants-api-hc-115) (HC-115, IMPLEMENTED at D2) lists, records, and revokes a patient's grants on this node, which then enforces them; its grant store is **MOCKED** (in memory, seeded from fictional grants) and its callers are not authenticated. The [research execution agent](#research-execution-agent-hc-183) is IMPLEMENTED at D3 for one bounded installed aggregate; it never executes submitted source code, and demo results remain `mocked: true` because its local repository is fictional. The [medication safety check](#medication-safety-check-hc-162) (HC-162, IMPLEMENTED at D2, [ADR-0008](../../docs/decisions/ADR-0008-medication-safety-check-host.md)) is a deterministic drug-drug interaction engine. By default its rules are **MOCKED** (fictional, not a validated source); the configuration can select the validated ONC high-priority list instead (HC-163, IMPLEMENTED at D3, [ADR-0009](../../docs/decisions/ADR-0009-validated-interaction-source.md)). With the Governance Node's public key configured, it verifies [Governance-signed synchronization authorizations](#signed-synchronization-authorizations-hc-214) on its own (HC-214, IMPLEMENTED at D4, opt-in, [ADR-0015](../../docs/decisions/ADR-0015-signed-federation-authorization.md)) instead of the MOCKED fictional decisions. It runs as an [OCI container image](#container-hc-220) (HC-220, IMPLEMENTED at D3, [ADR-0016](../../docs/decisions/ADR-0016-hospital-node-container-image.md)); each approved hospital receives it in an [installation package](../../infrastructure/packaging/hospital-node/README.md) (HC-221, IMPLEMENTED at D3); runtime detection and container health checks are PLANNED (HC-222, HC-223).

## Running locally

From this directory (POSIX shell; on Windows activate with `.venv\Scripts\activate`). Every server command needs `HOSPITAL_NODE_CONFIG` (see [Configuration](#configuration-hc-112)). The examples run Hospital A.

| Purpose | Command |
|---|---|
| Create environment | `python3 -m venv .venv && . .venv/bin/activate` |
| Install (dev) | `pip install -r requirements-dev.txt` |
| Server on the configured port | `HOSPITAL_NODE_CONFIG=config/hospital-a.demo.json python main.py` |
| Dev server with reload | `HOSPITAL_NODE_CONFIG=config/hospital-a.demo.json fastapi dev main.py --port 8101` |
| Tests | `pytest` |
| Lint / format check | `ruff check . && ruff format --check .` |
| Production-mode server (preview) | `HOSPITAL_NODE_CONFIG=config/hospital-a.demo.json fastapi run main.py --port 8101` |

`python main.py` listens on `127.0.0.1` at the configured port; `HOSPITAL_NODE_HOST` (an IP address) overrides the interface, and the [container image](#container-hc-220) sets it to `0.0.0.0`. `fastapi dev` and `fastapi run` ignore the configured port, so pass the matching `--port`. In PowerShell, set the variable first: `$env:HOSPITAL_NODE_CONFIG = "config/hospital-a.demo.json"`. To run several hospitals at once, start one process per configuration file, each in its own terminal.

## Configuration (HC-112)

One codebase runs as one process per hospital ([ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md)). At startup, `infrastructure/config.py` reads the JSON file named by the `HOSPITAL_NODE_CONFIG` environment variable:

| Field | Meaning |
|---|---|
| `node_ref` | Opaque node id, following the Federation contract's `OpaqueRef` pattern. |
| `organization_ref` | Opaque id of the hospital organization that controls this node. |
| `port` | Local port, 1024–65535. |
| `storage_dir` | This hospital's local storage directory. A relative path is resolved against the configuration file. Nothing reads or writes it yet: persistence is OPEN, so the mock repository stays in memory. `.storage/` is git-ignored. |
| `mock_clinical_records` | This hospital's fictional records file for the [mock clinical repository](#mock-clinical-repository-hc-113), resolved like `storage_dir`. The demo configurations point to their own file in [`demo-data/records/`](../../demo-data/records/). |
| `mock_access_grants` | Fictional patient access grants that seed the [access grant store](#access-grants-api-hc-115) used by the [MOCKED authorization check](#patient-history-api-hc-114), resolved like `storage_dir`. The demo configurations point to [`demo-data/access.json`](../../demo-data/access.json). |
| `mock_governance_decisions` | Fictional Governance decisions and synchronization requests for the same check. The demo configurations point to [`demo-data/governance.json`](../../demo-data/governance.json). |
| `mock_medication_rules` | Fictional deterministic interaction rules for the [medication safety check](#medication-safety-check-hc-162). The demo configurations point to [`demo-data/medication-rules.json`](../../demo-data/medication-rules.json). |
| `ai_services_url` | Optional. AI Services base URL for [advisory warning explanations](#ai-explanation-layer-hc-164); absent or `null` (default) keeps them off. [`config/hospital-a.ai-explanations.json`](config/hospital-a.ai-explanations.json) is Hospital A with `http://localhost:8600`: same identity and port as its demo configuration, so run one or the other. |
| `medication_rule_source` | Optional. `demo_fixture` (default) uses the fictional rules above; `onc_high_priority_2012` uses the [validated ONC snapshot](#validated-interaction-source-hc-163) bundled with the node. [`config/hospital-a.onc-rules.json`](config/hospital-a.onc-rules.json) is Hospital A with it: same identity and port, so run one or the other. |
| `governance_public_key` | Optional. The Governance Node's Ed25519 public key (PEM), resolved like `storage_dir`. With it, a synchronization decision counts only with a [Governance-signed authorization](#signed-synchronization-authorizations-hc-214) verified here, and the fictional decisions above are no longer used for them; absent (default), they are (MOCKED). An unreadable or non-Ed25519 key stops startup. [`config/hospital-b.signed-authorization.json`](config/hospital-b.signed-authorization.json) is Hospital B with the key written by the Governance Node's `python -m auth.create_signing_key`: same identity and port as its demo configuration, so run one or the other. |
| `governance_organization_ref` | Optional. The Governance / Ethics Authority whose signed authorizations this node accepts (`iss`); `org-governance` by default. |
| `notice` | Optional free-text note. |

The node refuses to start if the variable is unset, the file cannot be read, or any field is missing, unknown, or invalid. It never falls back to another hospital's identity.

The fictional demo configurations in [`config/`](config/) match the approved node organizations in [`demo-data/organizations.json`](../../demo-data/organizations.json) and the ports in the Federation [registry seed](../../services/federation/registry-seed.demo.json):

| File | Node | Organization | Port |
|---|---|---|---|
| `hospital-a.demo.json` | `node-hospital-a` | `org-hospital-a` | 8101 |
| `hospital-b.demo.json` | `node-hospital-b` | `org-hospital-b` | 8102 |
| `private-practice.demo.json` | `node-private-practice` | `org-private-practice` | 8104 |

Hospital C is still in onboarding in the demo data and has no node, so it has no configuration; ADR-0003 reserves port 8103 for it. This is demo configuration only: the identity is not authenticated, and it is not a production configuration or secret store.

## Mock clinical repository (HC-113)

MOCKED at D2. `application/clinical_repository.py` defines the `ClinicalRepository` port: one patient's records held by this node (`patient_records`) and record counts (`summary`). It does not check authorization; the [patient history API](#patient-history-api-hc-114) checks it before reading the repository. An unknown patient gets the same empty answer as a patient with no records here.

`domain/clinical_record.py` is a minimal hospital-local model: encounters, medications, and lab reports. Its field names follow the record shapes of [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml); the FHIR mapping is OPEN. References must be opaque ids and times must carry a UTC offset. Lab flags are kept as assigned at the source; the node does not interpret results.

`adapters/outbound/fixture_clinical_repository.py` implements the port. At startup it reads the one file named by `mock_clinical_records` and keeps the records in memory:

- The file must be marked `"fictional": true` and its `heldBy` must equal this node's `organization_ref`. Otherwise, or if a record is malformed, the node refuses to start. A node never loads another hospital's records.
- It is read-only. Nothing is written to `storage_dir` or back to `demo-data/`.
- Patient references are the dataset's ids (`pat-a`), as in the Federation contract; per-hospital local identifiers are not mapped.

This is not real clinical storage and not a DMI integration: the [DMI port](#dmi-port-hc-120) is defined (HC-120) and implemented by a MOCKED local DMI adapter (HC-121) and Hospital B's sample adapter over a simulated export (HC-123), but nothing imports records from either at runtime, and persistence is OPEN.

| Node | Encounters | Medications | Lab reports |
|---|---|---|---|
| Hospital A | 3 | 1 | 2 |
| Hospital B | 2 | 1 | 1 |
| Private practice | 2 | 2 | 0 |

## Patient history API (HC-114)

IMPLEMENTED at D2, with **MOCKED** records and **MOCKED** authorization. The node serves its side of [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml), so the Federation Service can ask it over real HTTP:

| Operation | Behavior |
|---|---|
| `GET /v1/federation/node` | Node descriptor: the configured `node_ref` and `organization_ref`, contract version `1.0`, status `online`, all three scopes, `mocked: true`. |
| `POST /v1/federation/queries` | One patient's history held by this node, inside the requested scope. |

How a query is answered (`application/get_patient_history.py`):

1. The request is parsed strictly. Missing, unknown, or invalid fields, a non-UUID `query_id`, an empty or duplicate scope, a blank purpose, or a non-opaque reference return `400 invalid_request` (`application/problem+json`) listing the fields.
2. The `AuthorizationVerifier` port decides whether the basis covers the query. It denies by default, and it is asked **before** the repository is read. A refusal returns `403 authorization_denied` with no entry and the same body whether or not the patient is known here.
3. Only the record types in `scope` are returned, each naming this node and organization as its `source`. A patient this node does not hold gets `entries: []`, the same as nothing inside the scope.
4. `provenance.mocked` is the repository's flag (`true`), and `answered_at` is the node's clock.

`adapters/outbound/fixture_authorization_verifier.py` is the default verifier, and it is MOCKED. With a `governance_public_key`, synchronization decisions are verified from the Governance Node's signature instead ([HC-214](#signed-synchronization-authorizations-hc-214)). The fixture verifier reads the fictional [`governance.json`](../../demo-data/governance.json) at startup, read-only, and looks grants up in this node's [access grant store](#access-grants-api-hc-115), seeded from the fictional [`access.json`](../../demo-data/access.json). The node refuses to start if either file is not marked fictional. It applies the same rules as the Federation Service's simulated nodes (HC-141):

- **Patient access grant** (`domain/access_grant.py`): active, not revoked, not expired at the node's clock, for this patient, issued to the requesting actor, same purpose, and a scope at least as wide as the query's.
- **Synchronization decision:** an approved decision on a synchronization request, still valid, that targets **this** node's organization, from the requesting organization, for this patient and purpose, with a wide enough scope.

The node trusts its own copy of each basis, never the `expires_at` stated in the request. This is not real authorization and not production security.

Not done at D2:

- Every query this node answers or refuses is recorded in its [audit trail](#audit-event-api-hc-116), in memory only.
- The descriptor always reports `online`: the records are in memory, so the node always reaches them. The demo data's disconnected private-practice DMI is shown only by the simulated nodes.
- A medication has only a start date, so its `occurred_at` is that date at midnight UTC.
- The node's identity is not authenticated, and callers are not authenticated; both are OPEN.

## Signed synchronization authorizations (HC-214)

IMPLEMENTED at D4, opt-in, not VALIDATED by a security review. [ADR-0015](../../docs/decisions/ADR-0015-signed-federation-authorization.md) records the decision. Configured with the Governance Node's public key (`governance_public_key`), this node verifies a query under a synchronization decision **on its own**, without asking the Governance Node: the query must carry the `signed_authorization` the Governance Node returned to the Federation Service for this exact exchange ([`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) 1.1.0; format in [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) 1.2.0).

It is accepted only if (`adapters/outbound/ed25519_authorization_reader.py`, then `domain/signed_authorization.py`):

- the header is exactly `alg: EdDSA`, the trusted key's RFC 7638 thumbprint as `kid`, and `typ: governance-authorization+jwt`, and the Ed25519 signature verifies with the configured key;
- the claims are exactly those of the contract, with opaque references;
- the issuer is `governance_organization_ref`, and this node's organization is in the audience;
- the decision, requesting organization, actor, patient, and purpose are the query's, and the query's scope is within the attested one;
- the node's clock is between the issue time (60 seconds of skew tolerated) and the expiry, five minutes at most.

Anything else, including no token, is `403 authorization_denied`, and the query is audited as denied. Patient access grants are still checked in this node's [grant store](#access-grants-api-hc-115). `GET /health` reports `synchronization_decisions`: `signed`, or `fixture` (MOCKED) without a key.

**Tests:** the reader against tampered claims, another key, unexpected headers (`none`, `HS256`, another `kid` or `typ`, `crit`), claims outside the contract, and malformed tokens; the coverage rules for every attested field, audience, issuer, time, and skew; patient grants left to the grant store (`test_signed_authorization.py`); and over HTTP against the contract, a configured Hospital B disclosing the attested scope for the runtime decision `dec-sync-001`, refusing without a covering token, auditing both, and refusing to start on an invalid key (`test_signed_federation_http.py`). The [demo](../governance-node/README.md#signed-federation-authorization-hc-214) was run with running Governance, Hospital B, and Federation processes: `ok` with signing on, `denied` with it off, and `403` for direct queries without the token, with a changed claim, for another patient, or for a wider scope.

Not done at D4: replay detection (a token can be reused for the same exchange until it expires); revocation before expiry; more than one trusted key; fetching the key from the Governance Node; authenticating the Federation Service; signed research authorizations. This is not production security.

Demo, with the three demo nodes running (one terminal each) and the Federation Service started with its demo seed in `http` mode ([Federation Service demo](../../services/federation/README.md#demo)): Dr. X's timeline request for Patient A is `complete`, with Hospital A answering 1 entry, Hospital B 2 (including Medication A, `MED-COAGULIX`), and the private practice 2; `provenance.mocked` is `true`. With another purpose, every node answers `denied`. `POST /v1/registry/discovery` reports each node `discovered`. A node can also be asked directly:

```bash
curl -s -X POST localhost:8102/v1/federation/queries -H 'content-type: application/json' -d '{
  "query_id": "0b9f6c2e-3d41-4a8e-9f57-1c2d3e4f5a6b",
  "patient_ref": "pat-a",
  "scope": ["medications"],
  "purpose": "Consultation de cardiologie",
  "requested_by": {"organization_ref": "org-hospital-a", "actor_ref": "clin-x"},
  "authorization": {"basis": "patient_access_grant", "ref": "grant-a-drx", "expires_at": "2026-10-24T09:00:00+01:00"}
}'
```

`grant-a-drx` expires on 2026-10-24. The node uses the real clock, so this request is refused with `403` after that date unless the fixtures are updated.

## Access grants API (HC-115)

IMPLEMENTED at D2 over a **MOCKED** grant store. The node serves [`patient-access-grants.v1.yaml`](../../contracts/api/patient-access/patient-access-grants.v1.yaml): the grants a patient gives one person, usually a clinician, to query their records held by this node, for a purpose, inside a scope, until a time.

| Operation | Behavior |
|---|---|
| `GET /v1/patients/{patient_ref}/access-grants` | `200`: every grant this node records for the patient, newest first, including expired and revoked ones. `status` is evaluated at the node's clock: `revoked` once revoked, `expired` from `expires_at` on, otherwise `active`. An unknown patient gets `grants: []`. |
| `POST /v1/patients/{patient_ref}/access-grants` | `201`: records a new active grant (`grantee_ref`, `scope`, `purpose`, `expires_at`) with a generated opaque `grant_ref` (`grant-<32 hex>`) and `granted_at` set to now. `400 invalid_request` when the body is outside the contract or `expires_at` is not in the future. |
| `POST /v1/patients/{patient_ref}/access-grants/{grant_ref}/revocation` | `200`: the grant with `revoked_at` set to now. Idempotent: a second revocation keeps the first time. An expired grant can still be revoked. `404 grant_not_found` when the grant is unknown here or belongs to another patient; both look the same. |

Every response names this node and carries `mocked: true`. Errors use `application/problem+json`; a non-opaque path reference is a `400`.

The node enforces what this API records. The [patient history API](#patient-history-api-hc-114) checks grants in the same store, so a grant counts as soon as it is recorded and a query citing it is refused from its revocation on; both queries appear in the [audit trail](#audit-event-api-hc-116).

The rules (status, revocation, validity, what a grant allows) live in `domain/access_grant.py`, the use cases in `application/manage_access_grants.py` behind an `AccessGrantStore` port, and the wire mapping in `adapters/inbound/http/access_grants.py`. `adapters/outbound/in_memory_access_grant_store.py` is MOCKED:

- It is seeded at startup from the fictional `access.json` and refuses to start on a file not marked fictional or a malformed grant. Changes live in memory only: they are lost on restart and never written to `demo-data/` or `storage_dir`. Persistence is OPEN.
- Each node keeps its own copy. A grant recorded on Hospital B is unknown to Hospital A, and a revocation on one node does not reach the others. How one patient's consent reaches every node holding their records is OPEN ([open questions](../../docs/OPEN_QUESTIONS.md)). The Governance Node reads this API when it evaluates a synchronization targeting this node (HC-136): a revocation recorded here stops that synchronization at its next authorization check.
- **Callers are not authenticated.** Anyone who can reach the node can list, record, or revoke any patient's grants. Who may call it (the patient, a delegate, the Patient App) is OPEN. This is not production consent management.
- Recording and revoking a grant are not audit events: the audit-event contract (HC-116) covers queries only.
- Delegations to relatives, restriction or erasure requests, grants without an expiry, and checking the grantee against a people registry are not served. No Patient App calls this API yet.

Demo, on Hospital B (port 8102), checked with Hospital A and B running side by side: `GET /v1/patients/pat-a/access-grants` lists `grant-a-drx` (active) and `grant-a-ines` (expired). Patient A records the contract's `patientAGrantsInes` grant; Dr. Ines's query for Patient A's medications under it returns `med-b-leila-coagulix` on Hospital B, is refused on Hospital A, and is refused on Hospital B after revocation:

```bash
curl -s localhost:8102/v1/patients/pat-a/access-grants
curl -s -X POST localhost:8102/v1/patients/pat-a/access-grants -H 'content-type: application/json' -d '{
  "grantee_ref": "clin-ines", "scope": ["medications"],
  "purpose": "Consultation de médecine interne", "expires_at": "2026-11-10T10:00:00+01:00"
}'
curl -s -X POST localhost:8102/v1/patients/pat-a/access-grants/<grant_ref>/revocation
```

## Audit event API (HC-116)

IMPLEMENTED at D2; events are kept **in memory only**. The node keeps its own audit trail of the patient history queries it handles and serves it as [`hospital-audit-events.v1.yaml`](../../contracts/api/hospital-audit/hospital-audit-events.v1.yaml). There is no central audit store: each node answers only for itself.

What is recorded (`application/get_patient_history.py`, `domain/audit_event.py`):

- One event per query the node answers (`disclosed`) or refuses (`denied`): event id, time, `query_id` from the Federation Service, patient, requesting organization and actor, purpose, scope, authorization basis and reference, and the references of the records disclosed.
- **No clinical content.** Disclosed records are named by reference only (for example `med-b-leila-coagulix`), never by code, dosage, or result.
- A refusal is recorded with no disclosed reference. A request rejected as invalid (`400`) is not recorded: nothing was parsed or disclosed.
- **No audit, no disclosure.** The event is recorded before the answer is returned; if recording fails, the error propagates and nothing is disclosed.
- Append-only: the API has no write or delete operation.

`GET /v1/audit/events` lists events newest first. Optional filters: `patient_ref`, `query_id`, `outcome` (`disclosed` or `denied`), and `limit` (1–500, default 50). An unknown, repeated, or invalid parameter returns `400 invalid_request` (`application/problem+json`). The response carries the node's identity and `durable: false`.

Not done at D2:

- **Not durable.** `adapters/outbound/in_memory_audit_log.py` keeps events in the process; a restart starts an empty trail, and nothing is written to `storage_dir`. Persistence is OPEN ([ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md)).
- **Readers are not authenticated.** The trail names patients and requesters, so who may read it is a real question; it is OPEN. Keep the node on `127.0.0.1` and never expose it: `python main.py` listens there, but `fastapi run` listens on every interface unless given `--host 127.0.0.1`.
- Only patient history queries are audited. Descriptor reads, health checks, and anchoring audit proofs in the Governance ledger (OPTIONAL) are not part of this version.

Demo, after the Federation timeline request in the [patient history demo](#patient-history-api-hc-114) and the same request with another purpose:

```bash
curl -s 'localhost:8102/v1/audit/events?patient_ref=pat-a'
```

Hospital B lists two events, newest first: `denied` for the other purpose with no disclosed reference, then `disclosed` with `enc-b-2026-leila` and `med-b-leila-coagulix`. Each event carries the Federation Service's `query_id`, so the same query can be traced in every node's trail. Hospital A and the private practice list only their own events.

## Research execution agent (HC-183)

IMPLEMENTED at D3 against [`research-node-execution.v1.yaml`](../../contracts/api/research/research-node-execution.v1.yaml). `POST /v1/research-executions` accepts a bounded job and `GET /v1/research-executions/{execution_id}` returns its terminal controlled outcome.

Before reading local data, the node verifies that the target is this exact node and organization, the authorization names the Governance authority, the organization and requested variables are approved, and `valid_until` has not passed. This is deterministic envelope validation, **not authenticated Governance verification**: signatures, service identity, and production authorization remain OPEN. A denial returns the same response regardless of local data.

The executor supports only the preinstalled aggregate identified by the HC-180 canonical SHA-256 and `compute` entry point, with `hba1c` as its only variable and encounter-date population filters. It does not download or execute the submitted `artifact_ref`; arbitrary Python and package installation remain out of scope. Age filters fail explicitly because this Hospital Node does not own local demographic data in the current model.

HC-186 (D4) runs that installed aggregate in a separate Python process with `-I -S`, an empty environment, a temporary working directory, no patient references in its JSON payload, and fixed input/output/record quotas. A Python audit hook denies post-startup file access, imports, network calls, shell/process creation, while the parent enforces a two-second wall-time limit. POSIX runtimes additionally apply CPU, address-space, file-size, and child-process `rlimit`; Windows honestly reports `parent_enforced` because those OS limits are unavailable in this adapter. Each controlled result carries a `sandbox` evidence object. This is a concrete defense-in-depth boundary for one trusted installed worker, **not** container-grade production isolation and not permission to execute submitted code.

The executor reads only this node's repository through a local application port. It returns:

- `empty` when no local subject matches;
- `suppressed` with no columns or rows when the cohort is smaller than `minimum_cell_size`;
- `released` only as aggregate cells when the minimum is met;
- `failed`, `denied`, `invalid`, `conflict`, and `not found` states without exposing whether a patient exists.

Execution state is process-local and lost on restart. The canonical demo repository is explicitly MOCKED, so accepted and terminal responses carry `mocked: true`. The HTTP agent, authorization rules, aggregate, sandbox, suppression, and provenance behavior are implemented; the data source is not production data or storage. Cross-node aggregation and output validation live in the Research Service (HC-184/HC-185). Research audit, durable persistence, authentication, container isolation, and general code execution are not implemented.

## Medication safety check (HC-162)

IMPLEMENTED at D2 against [`medication-safety-check.v1.yaml`](../../contracts/api/medication-safety/medication-safety-check.v1.yaml). [ADR-0008](../../docs/decisions/ADR-0008-medication-safety-check-host.md) places the check on the Hospital Node serving the clinician. `POST /v1/medication-safety-checks` compares a proposed medication with the current medications the caller sends, and returns drug-drug interaction warnings for clinician review. **The safety source is a deterministic rule set, never a model**, and the check never blocks or approves a prescription.

- **Engine** ([`domain/medication_safety.py`](domain/medication_safety.py), standard library only):
  - A medication is identified by its code in the rule set's code system, otherwise by its exact name or one of the rule set's synonyms (case, accents, and apostrophe style ignored).
  - A code and a name that point to different medications are `ambiguous_medication`; one the rules do not know is `not_in_rule_source`. Nothing is guessed.
  - Only `active` statements are evaluated. A `stopped` one is not current and is skipped; an `unknown` status is reported as `status_unknown`.
  - Warnings come out most severe first, each with its rule, the conflicting statement, and the organization it came from.
- **Rules** come through the `InteractionRuleSource` port ([`application/check_medication_safety.py`](application/check_medication_safety.py)). By default, [`adapters/outbound/fixture_interaction_rules.py`](adapters/outbound/fixture_interaction_rules.py) reads the fictional HC-161 rule set at startup. It refuses a file that is not fictional, is marked validated, or is not a consistent deterministic rule set. Every result then says `provenance.mocked: true`, and its notice says the rules are fictional. The [validated source](#validated-interaction-source-hc-163) is the other adapter.
- **No check is ever reported as "no warnings".** If the rules are unavailable, or they cannot identify the proposed medication, the answer is `503 safety_check_unavailable` with "No check was performed". `no_warnings_found` lists the medications that could not be evaluated, and its notice says it is not a statement of safety.
- **Stateless:** the node does not read its own clinical repository for the check, stores nothing from the request, and does not audit it (the audit contract has no such event yet). Callers are not authenticated (demo depth). `explanation` is `null` unless the node is configured for [AI explanations](#ai-explanation-layer-hc-164).

Demo (Hospital A's node, the canonical scenario of steps 12–13):

```bash
curl -s -X POST localhost:8101/v1/medication-safety-checks -H 'content-type: application/json' -d '{
  "patient_ref": "pat-a", "requested_by": "clin-x",
  "proposed_medication": {"name": "Dolorane", "code": null},
  "current_medications": [
    {"statement_ref": "med-b-leila-coagulix", "medication": {"name": "Coagulix", "code": null},
     "status": "active", "source": {"organization_ref": "org-hospital-b"}},
    {"statement_ref": "med-pp-leila-tensiorel", "medication": {"name": "Tensiorel", "code": null},
     "status": "active", "source": {"organization_ref": "org-private-practice"}}]}'
```

It returns one `major` warning ("Risque hémorragique accru.", rule `rule-coagulix-dolorane`, Coagulix from `org-hospital-b`); Tensiorel gives none. Run on 2026-10-11 against a live node:
- Bronchair for Nour came back as `not_in_rule_source` with `no_warnings_found`.
- An unknown proposed medication gave a `503`.

The tests run every HC-161 check case through the route, and each answer matches its expected result and the contract.

Not done: any product calling the check, and a real medication terminology (OPEN; the demo uses the fictional `urn:hackcure:demo:medication`).

### Validated interaction source (HC-163)

IMPLEMENTED at D3; source and matching decided by [ADR-0009](../../docs/decisions/ADR-0009-validated-interaction-source.md). With `medication_rule_source: onc_high_priority_2012`, [`adapters/outbound/validated_snapshot_rules.py`](adapters/outbound/validated_snapshot_rules.py) reads the ONC high-priority drug–drug interaction list at startup. That list is Phansalkar et al., JAMIA 2012;19(5):735–743, doi:10.1136/amiajnl-2011-000612: a peer-reviewed expert consensus of interactions "contraindicated for concurrent use". Results are `mocked: false`, with `rule_source.kind: validated_source`, the source row as `rule_id`, and the citation as `reference`.

- **Snapshot** ([`reference/onc-high-priority-ddi-2012.json`](reference/onc-high-priority-ddi-2012.json)): a hand transcription of Table 2's final membership column, checked against the table on 2026-10-11.
  - 13 interactions over 89 ingredients become 362 `contraindicated` pairs. Each row keeps exactly the members it lists; row 25's CYP3A4 inhibitors, for example, do not include fosamprenavir.
  - Spelling corrections of the printed table are recorded (Esmoprazole, Lisdexamefetamine, Voreconazole, Moclobamide). So are the two rows left out: TCAs + MAO inhibitors, which lists no TCA members, and QT-prolonging pairs, which defer to the separately licensed CredibleMeds list.
  - Only the drug pairs and the citation are stored, no text of the article. A test freezes the member counts per row; a changed transcription needs a new snapshot version.
- **Matching:** by ingredient name, the English name printed plus French and other INN synonyms (*ciprofloxacine*, *rifampicine*, *péthidine*, *millepertuis*, …). No terminology is adopted. Brand names, combinations, names with a dose, and unlisted drugs are `not_in_rule_source`, never assumed safe.
- **Scope, stated in every answer:** the list is a **minimum** set from 2012, not exhaustive; most interactions are not in it. The notice says so, and that no warning does not mean the combination is safe. Fictional demo medicines are unknown to it: proposing one gives a `503`.

Demo, run with `HOSPITAL_NODE_CONFIG=config/hospital-a.onc-rules.json python main.py` on 2026-10-11:
- Proposing *Simvastatine* to a patient taking *Clarithromycine* (from `org-hospital-b`) and *Amlodipine* gave one `contraindicated` warning, `onc-2012-row-25`, with the citation. *Amlodipine* came back as `not_in_rule_source`, with `mocked: false`.
- *Dolorane* (fictional) gave a `503`.

Not done: a broader licensed source and a medication terminology (OPEN), and re-transcription if the list is revised.

### AI explanation layer (HC-164)

IMPLEMENTED at D3. When `ai_services_url` is configured, each warning gets an advisory plain-language explanation. It is added **after** the deterministic check has produced the warning, and the explanation never creates, removes, or changes one.

- **How:** the `WarningExplainer` port ([`application/check_medication_safety.py`](application/check_medication_safety.py)) is implemented by [`adapters/outbound/ai_services_warning_explainer.py`](adapters/outbound/ai_services_warning_explainer.py). It calls AI Services' [`medication-warning-explanation.v1.yaml`](../../contracts/api/ai/medication-warning-explanation.v1.yaml) (HC-156) once per warning, in parallel, with a 30 s timeout. AI Services checks model text and falls back to a deterministic template itself.
- **What leaves the hospital:** only the warning's content (severity, summary, the two medication names, the rule source) and the opaque `requested_by`. No patient reference, no other medications. With AI Services in model mode, that content goes on to the model provider (ADR-0006). This is why the layer is **off unless a hospital configures it**: whether clinical text may leave the hospital boundary is OPEN.
- **What comes back:** the answer is kept only if it is an advisory explanation of that very warning, in the contract's shape. Anything else, an error, or a timeout means `explanation: null`; the warning is complete without it and the check still answers `200`. When at least one explanation is attached, the notice adds that explanations are advisory and never decide whether a warning exists.

Run live on 2026-10-11 with `config/hospital-a.ai-explanations.json` and AI Services on port 8600, on the canonical demo (Dolorane for Patient A):
- **Template mode:** the deterministic template's text.
- **Model mode:** Claude's checked text ("Une interaction de sévérité majeure est signalée entre … Dolorane, et … Coagulix …"), in about 15 s.
- **AI Services stopped:** the same `major` warning with `explanation: null`.

Not done: no product shows the explanation yet, and explanations for patients are out of scope.

## Container (HC-220)

IMPLEMENTED at D3 and checked locally with Docker Desktop 29.1 (Linux engine). [ADR-0016](../../docs/decisions/ADR-0016-hospital-node-container-image.md) records the decision.

**One image for every hospital.** [`Dockerfile`](Dockerfile) builds from this directory alone. The image contains Python 3.12 (official slim image, pinned by digest), the pinned `requirements.txt`, and the Node's code, including the ONC reference snapshot. It contains no hospital configuration, no records, no tests, and no development dependencies ([`.dockerignore`](.dockerignore)). The Node runs as the unprivileged `hospital-node` user (uid 10001), which cannot write the code.

**What a hospital mounts.** The image reads its configuration from `/etc/hospital-node/node.json` (`HOSPITAL_NODE_CONFIG`) and refuses to start without one, or with records held by another organization. The files the configuration names are mounted next to it, read-only. `storage_dir` is `/var/lib/hospital-node`, which nothing writes yet. Inside the container the Node listens on `0.0.0.0` at the configured port.

**Demo composition.** [`infrastructure/docker/hospital-node/compose.yaml`](../../infrastructure/docker/hospital-node/compose.yaml) runs Hospital A, Hospital B, and the private practice from the same image, with the [container configurations](../../infrastructure/docker/hospital-node/) next to it. Each has the same identity and port as its demo configuration, but only its own fictional records file. Each container runs on a read-only filesystem with a `tmpfs` at `/tmp` for the research sandbox, drops every capability, sets `no-new-privileges`, and is published on `127.0.0.1` only, because callers are not authenticated. From the repository root:

```bash
docker compose -f infrastructure/docker/hospital-node/compose.yaml up --build -d
curl -s localhost:8102/health
docker compose -f infrastructure/docker/hospital-node/compose.yaml down
```

Services on the host, such as the Federation Service with its demo seed, reach the nodes at `localhost:8101`, `8102`, and `8104` as before. The containers are a replacement for running `python main.py` in three terminals, so do not run both at once.

Checked by hand with the composition running:

- `/health` answers on each port, with each hospital's own record counts.
- Patient A's [federated query](../../services/federation/README.md#demo) is `complete`, with 1, 2, and 2 entries.
- A research execution completes, and its sandbox reports `os_resource_limits: posix_rlimit`. On a Windows host outside a container it reports `parent_enforced`.
- Writes to `/app` and to the mounted data fail with a read-only file system error.
- Without a configuration, or with Hospital B's records under Hospital A's configuration, the Node stops at startup.

[`tests/test_container_layout.py`](tests/test_container_layout.py) runs without Docker. For each container it rebuilds the mounted `/etc/hospital-node` from the composition and boots the app on it. It also checks that every mount is read-only, that a container sees only its own records, that ports are published on loopback at the configured port, and the user and image exclusions.

A hospital installs its own Node from an [installation package](../../infrastructure/packaging/hospital-node/README.md) (HC-221): the image, this configuration layout, and a helper that verifies and starts it, never its records.

Not done at D3: a container health check (HC-223), runtime detection (HC-222), an image registry or signing, and hosting. A container is a process boundary, not production security. Callers are unauthenticated, data is MOCKED, and there is no persistence.

## Health endpoint (HC-111)

`GET /health` is a liveness check. It returns `200` with the node kind, version, the configured `node_ref` and `organization_ref`, its capabilities (including `research_execution`, `isolated_research_sandbox`, and `medication_safety_check`), the clinical repository's record counts and `mocked` flag, and a notice stating that the identity comes from fictional demo configuration, that the repository and authorization are MOCKED (unless synchronization decisions are verified from signatures, reported as `synchronization_decisions`), that research execution is bounded, that the process sandbox is not production container isolation, that the audit trail is in memory and its readers are not authenticated, and that it is not a production health check:

```json
{"status": "ok", "node": "hospital-node", "version": "0.4.0", "node_ref": "node-hospital-a", "organization_ref": "org-hospital-a", "capabilities": ["patient_history", "audit_events", "access_grants", "research_execution", "isolated_research_sandbox", "medication_safety_check"], "clinical_records": {"mocked": true, "encounters": 3, "medications": 1, "lab_reports": 2}, "synchronization_decisions": "fixture", "notice": "Hospital Node (HC-111 to HC-116, HC-162, HC-183, HC-186). ..."}
```

The counts contain no patient data.

It does not check storage, DMI connectivity, or Federation reachability; none exists yet. Deployment health checks are PLANNED in HC-223. Besides `/health`, the Federation, audit, access-grant, research-execution, and medication-safety paths, only FastAPI's generated `/openapi.json` and `/docs` are served.

## Layout

```text
instances/hospital-node/
├── main.py                     # composition root: loads configuration, builds the FastAPI app
├── config/                     # fictional per-hospital demo configurations; hospital-b.dmi.json is Hospital B's DMI adapter configuration
├── domain/                     # Node identity/status, clinical records, access/audit, research execution values, and the medication interaction engine — stdlib only
├── application/                # Hospital use cases and their repository, authorization, audit, grant, research, interaction rule, and DMI ports
├── adapters/inbound/http/      # health, Federation, audit, access-grant, research-execution, and medication-safety routers
├── adapters/outbound/          # fixture repositories/verifiers, the Ed25519 signed-authorization reader (HC-214), interaction rules, installed aggregate, and in-memory stores
├── infrastructure/             # configuration loading and validation
├── Dockerfile, .dockerignore   # container image recipe: code only, no hospital configuration or data (HC-220)
├── reference/                  # validated reference data read at startup (the ONC interaction snapshot, HC-163)
├── adapters/dmi/               # hospital-local DMI Adapters (port, HC-120; MOCKED local adapter, HC-121; mapping strategy, HC-122; Hospital B's adapter, HC-123)
├── contracts/                  # reserved for Node-local contract documents
└── tests/                      # domain, use case, adapter, app, and layer-boundary tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library.

## DMI port (HC-120)

DEFINED at D1. The Node owns `DmiSource` ([`application/dmi_source.py`](application/dmi_source.py)): `describe()` and `extract_patient(PatientIdentity)`, returning a `DmiExtract` ([`domain/dmi.py`](domain/dmi.py)) of one patient's records in this Node's canonical model plus the entries the adapter could not map. Each hospital's adapter implements it under [`adapters/dmi/`](adapters/dmi/README.md), which documents the rules every adapter keeps and the conformance check ([`tests/dmi_port_contract.py`](tests/dmi_port_contract.py)) its tests must pass.

Two adapters implement it:

- The **MOCKED** local DMI adapter (HC-121, D2, [`adapters/dmi/mock_local_dmi.py`](adapters/dmi/mock_local_dmi.py)): a simulated DMI built from this hospital's fictional records file and the local identifiers its organization gives patients in [`people.json`](../../demo-data/people.json). It passes the port conformance check for all three demo nodes; see the [adapter README](adapters/dmi/README.md#mock-local-dmi-adapter-hc-121).
- **Hospital B's** sample hospital-specific adapter (HC-123, D3, [`adapters/dmi/zitoun_sih_export.py`](adapters/dmi/zitoun_sih_export.py)), IMPLEMENTED against a simulated DMI: it reads the fictional nightly export of Hospital B's fictional DMI ([`demo-data/dmi/hospital-b-export.json`](../../demo-data/dmi/hospital-b-export.json)) in that DMI's own format and maps its local codes with Hospital B's mapping tables, kept in its local adapter configuration ([`config/hospital-b.dmi.json`](config/hospital-b.dmi.json)). Its extracts reproduce Hospital B's canonical fixture records; see the [adapter README](adapters/dmi/README.md#sample-hospital-specific-adapter-hospital-b-hc-123).

Both follow the [mapping strategy](adapters/dmi/README.md#mapping-strategy-hc-122) (HC-122, D2): local codes map to the canonical model only through a hospital's explicit tables, and entries that cannot map are rejected with a shared reason (`missing_field`, `invalid_value`, `unmapped_code`).

Nothing calls the port at runtime yet: `main.py` builds neither adapter, the Node configuration names none, no real DMI is connected, `/health` is unchanged, and the Node's records still come from the MOCKED fixture repository. When extraction runs and where its results go are OPEN. No central service implements or calls the port.

## Responsibilities and owned concepts

- Local clinical integration and canonical/FHIR representation.
- Hospital-specific DMI Adapter boundary at `adapters/dmi/`, behind the Node-owned [DMI port](#dmi-port-hc-120).
- Local storage and clinical source-data control.
- Consent/authorization enforcement at the local boundary.
- Local audit generation and Federation interface.
- Per-hospital configuration loading, liveness health check, patient history API, in-memory audit trail, access grants API, bounded research execution agent, and deterministic medication safety check (IMPLEMENTED); clinical repository, patient-query authorization check, grant store, research data, and interaction rules are MOCKED; future delegations, durable storage, authenticated identity/RBAC, and events.

## Communication boundaries

The Node communicates through versioned API, event, and Federation contracts. `contracts/` is reserved for Node-owned local ports; repository-level cross-component contracts live at `/contracts`. Each hospital owns its DMI implementation and configuration.

## Non-responsibilities

The Hospital Node does not own ethics approval, global research approval, company billing, or central blockchain authority. Central services must not access its database or DMI/HIS directly.

## Expected contracts

Each Hospital Node must provide [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) (HC-140): a node descriptor and authorized, scoped patient queries that the node enforces itself. This runtime serves both operations (HC-114) with MOCKED records and MOCKED authorization, and audits every query (HC-116).

It also provides [`hospital-audit-events.v1.yaml`](../../contracts/api/hospital-audit/hospital-audit-events.v1.yaml) (HC-116): its own audit trail of those queries; and [`patient-access-grants.v1.yaml`](../../contracts/api/patient-access/patient-access-grants.v1.yaml) (HC-115): the patient access grants it records and enforces.

It provides [`medication-safety-check.v1.yaml`](../../contracts/api/medication-safety/medication-safety-check.v1.yaml) (HC-162, [ADR-0008](../../docs/decisions/ADR-0008-medication-safety-check-host.md)) with a deterministic engine over MOCKED fictional rules by default, or the validated ONC high-priority list (HC-163, [ADR-0009](../../docs/decisions/ADR-0009-validated-interaction-source.md)).

The D1 research execution contract at [`contracts/api/research/research-node-execution.v1.yaml`](../../contracts/api/research/research-node-execution.v1.yaml) is IMPLEMENTED by the HC-183 agent for the bounded installed aggregate and extended by HC-186 with sandbox evidence. Authenticated Governance verification, general code execution, container-grade isolation, package distribution, durable state, research audit, and production disclosure review remain PLANNED or OPEN.

PLANNED local clinical API, consent/authorization, and health contracts. The DMI port (HC-120) is a Node-internal `typing.Protocol`, not a contract document. `/health` is Node-local and has no versioned contract.

The Federation Service calls this runtime over real HTTP at the `base_url` it has in the node registry: `GET /v1/federation/node` for capability discovery (HC-143) and `POST /v1/federation/queries` for federated queries (HC-145). This runtime serves both, so a running node is `discovered` and answers queries. The demo ports in `config/` (8101, 8102, 8104) match the Federation Service's [`registry-seed.demo.json`](../../services/federation/registry-seed.demo.json).
