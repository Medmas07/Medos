# Hospital Node

## Purpose and status

CONFIRMED autonomous hospital-controlled boundary. Its stack (Python + FastAPI, one process per hospital from one codebase, flat layer layout that keeps `adapters/dmi/`) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-110): a FastAPI app with Clean/Hexagonal layers, pinned dependencies, and tests. Per-hospital configuration loading is IMPLEMENTED at D2 (HC-112). Its clinical repository is **MOCKED** at D2 (HC-113): fictional demo records, read-only, in memory. It serves `GET /health` (HC-111, IMPLEMENTED at D2) and the [patient history API](#patient-history-api-hc-114) (HC-114, IMPLEMENTED at D2): its side of the Federation contract, whose authorization check is **MOCKED** against fictional grants and decisions. Queries are not audited yet; the consent/access and audit APIs (HC-115, HC-116) are PLANNED. It is expected to become a separately packaged/containerized instance; container choices remain OPEN.

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

`python main.py` listens on `127.0.0.1` at the configured port. `fastapi dev` and `fastapi run` ignore the configured port, so pass the matching `--port`. In PowerShell, set the variable first: `$env:HOSPITAL_NODE_CONFIG = "config/hospital-a.demo.json"`. To run several hospitals at once, start one process per configuration file, each in its own terminal.

## Configuration (HC-112)

One codebase runs as one process per hospital ([ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md)). At startup, `infrastructure/config.py` reads the JSON file named by the `HOSPITAL_NODE_CONFIG` environment variable:

| Field | Meaning |
|---|---|
| `node_ref` | Opaque node id, following the Federation contract's `OpaqueRef` pattern. |
| `organization_ref` | Opaque id of the hospital organization that controls this node. |
| `port` | Local port, 1024–65535. |
| `storage_dir` | This hospital's local storage directory. A relative path is resolved against the configuration file. Nothing reads or writes it yet: persistence is OPEN, so the mock repository stays in memory. `.storage/` is git-ignored. |
| `mock_clinical_records` | This hospital's fictional records file for the [mock clinical repository](#mock-clinical-repository-hc-113), resolved like `storage_dir`. The demo configurations point to their own file in [`demo-data/records/`](../../demo-data/records/). |
| `mock_access_grants` | Fictional patient access grants for the [MOCKED authorization check](#patient-history-api-hc-114), resolved like `storage_dir`. The demo configurations point to [`demo-data/access.json`](../../demo-data/access.json). |
| `mock_governance_decisions` | Fictional Governance decisions and synchronization requests for the same check. The demo configurations point to [`demo-data/governance.json`](../../demo-data/governance.json). |
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

This is not real clinical storage and not a DMI integration: the DMI Adapter (HC-120+) is PLANNED and persistence is OPEN.

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

`adapters/outbound/fixture_authorization_verifier.py` is the only verifier, and it is MOCKED. How a node verifies a basis with the Governance Node is OPEN, and no Governance Node runs, so it reads the fictional [`access.json`](../../demo-data/access.json) and [`governance.json`](../../demo-data/governance.json) at startup, read-only, and refuses to start if either is not marked fictional. It applies the same rules as the Federation Service's simulated nodes (HC-141):

- **Patient access grant:** active, not revoked, not expired at the node's clock, for this patient, issued to the requesting actor, same purpose, and a scope at least as wide as the query's.
- **Synchronization decision:** an approved decision on a synchronization request, still valid, that targets **this** node's organization, from the requesting organization, for this patient and purpose, with a wide enough scope.

The node trusts its own copy of each basis, never the `expires_at` stated in the request. This is not real authorization and not production security.

Not done at D2:

- **Audit is PLANNED (HC-116).** The contract says every query is recorded in the node's audit trail; this runtime does not record queries yet.
- The descriptor always reports `online`: the records are in memory, so the node always reaches them. The demo data's disconnected private-practice DMI is shown only by the simulated nodes.
- A medication has only a start date, so its `occurred_at` is that date at midnight UTC.
- The node's identity is not authenticated, and callers are not authenticated; both are OPEN.

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

## Health endpoint (HC-111)

`GET /health` is a liveness check. It returns `200` with the node kind, version, the configured `node_ref` and `organization_ref`, its `capabilities` (`patient_history`), the clinical repository's record counts and `mocked` flag, and a notice stating that the identity comes from fictional demo configuration, that the repository and authorization are MOCKED, that queries are not audited yet, and that it is not a production health check:

```json
{"status": "ok", "node": "hospital-node", "version": "0.1.0", "node_ref": "node-hospital-a", "organization_ref": "org-hospital-a", "capabilities": ["patient_history"], "clinical_records": {"mocked": true, "encounters": 3, "medications": 1, "lab_reports": 2}, "notice": "Hospital Node (HC-111 to HC-114). ..."}
```

The counts contain no patient data.

It does not check storage, DMI connectivity, or Federation reachability; none exists yet. Deployment health checks are PLANNED in HC-223. Besides `/health` and the two Federation operations, only FastAPI's generated `/openapi.json` and `/docs` are served.

## Layout

```text
instances/hospital-node/
├── main.py                     # composition root: loads configuration, builds the FastAPI app
├── config/                     # fictional per-hospital demo configurations
├── domain/                     # NodeIdentity, NodeStatus, clinical records, history query — stdlib only
├── application/                # get_node_status and get_patient_history use cases; ClinicalRepository and AuthorizationVerifier ports; imports only domain
├── adapters/inbound/http/      # /health and /v1/federation routers, Pydantic wire models
├── adapters/outbound/          # MOCKED fixture clinical repository (HC-113) and authorization verifier (HC-114)
├── infrastructure/             # configuration loading and validation
├── adapters/dmi/               # PLANNED hospital-local DMI Adapter (HC-120+)
├── contracts/                  # reserved for Node-local contract documents
└── tests/                      # domain, use case, adapter, app, and layer-boundary tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library.

## Responsibilities and owned concepts

- Local clinical integration and canonical/FHIR representation.
- Hospital-specific DMI Adapter boundary at `adapters/dmi/`.
- Local storage and clinical source-data control.
- Consent/authorization enforcement at the local boundary.
- Local audit generation and Federation interface.
- Per-hospital configuration loading, liveness health check, and patient history API (IMPLEMENTED); clinical repository and authorization check (MOCKED); future consent/access and audit APIs, authenticated identity/RBAC, and events.

## Communication boundaries

The Node communicates through versioned API, event, and Federation contracts. `contracts/` is reserved for Node-owned local ports; repository-level cross-component contracts live at `/contracts`. Each hospital owns its DMI implementation and configuration.

## Non-responsibilities

The Hospital Node does not own ethics approval, global research approval, company billing, or central blockchain authority. Central services must not access its database or DMI/HIS directly.

## Expected contracts

Each Hospital Node must provide [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) (HC-140): a node descriptor and authorized, scoped patient queries that the node enforces itself. This runtime serves both operations (HC-114) with MOCKED records and MOCKED authorization; it does not audit queries yet.

PLANNED local clinical API, DMI port, consent/authorization, audit-event, and research-execution contracts. `/health` is Node-local and has no versioned contract.

The Federation Service calls this runtime over real HTTP at the `base_url` it has in the node registry: `GET /v1/federation/node` for capability discovery (HC-143) and `POST /v1/federation/queries` for federated queries (HC-145). This runtime serves both, so a running node is `discovered` and answers queries. The demo ports in `config/` (8101, 8102, 8104) match the Federation Service's [`registry-seed.demo.json`](../../services/federation/registry-seed.demo.json).
