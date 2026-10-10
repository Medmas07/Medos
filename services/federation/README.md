# Federation Service

## Purpose and status

Coordination capability for authorized communication among autonomous Nodes. Python + FastAPI per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md).

- **IMPLEMENTED (D2):**
  - the federated patient query, [`federated-patient-query.v1.yaml`](../../contracts/federation/federated-patient-query.v1.yaml) (HC-141). It asks each registered Hospital Node, merges the answers into a transient timeline, and reports a status for each node.
  - the node registry, [`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml) (HC-142): register, update, list, get, and remove nodes. Federated queries ask the nodes listed there. It is kept in memory, and its Governance approval references are **not verified**.
- **MOCKED:** the Hospital Nodes. The Hospital Node runtime (HC-110) is a skeleton with no Federation endpoint yet, so each organization with a node in [`demo-data/`](../../demo-data/README.md) is simulated in process. **This is not node-to-node exchange and not production security.**
- **PLANNED:** capability discovery (HC-143), Governance verification of authorizations and approvals (HC-144, HC-131), real node-to-node calls (HC-145), persistent registry storage, authentication of registry writes, and audit events.

## Running locally

From this directory (POSIX shell; on Windows activate with `.venv\Scripts\activate`):

| Purpose | Command |
|---|---|
| Create environment | `python3 -m venv .venv && . .venv/bin/activate` |
| Install (dev) | `pip install -r requirements-dev.txt` |
| Dev server with reload, demo nodes registered | `FEDERATION_REGISTRY_SEED=registry-seed.demo.json fastapi dev main.py --port 8300` |
| Tests | `pytest` |
| Lint / format check | `ruff check . && ruff format --check .` |
| Production-mode server (preview), empty registry | `fastapi run main.py --port 8300` |

`GET /health` reports `"mocked": true` and a notice that the nodes are simulated and the registry is in memory.

**The registry starts empty.** Nodes are registered through the API or, at startup, from the JSON file named by `FEDERATION_REGISTRY_SEED`. Seed entries go through the same validation as the API, and an invalid seed stops startup. [`registry-seed.demo.json`](registry-seed.demo.json) registers the three demo nodes: Hospital A, Hospital B, and the private practice. Hospital C is in onboarding and is not registered. Because the registry is in memory, registrations made through the API are lost on restart.

## Demo

Start the service with the demo seed (see above). The registry lists the three demo nodes, each with `approval.verified: false`:

```bash
curl -s localhost:8300/v1/registry/nodes
```

Dr. X opens Patient A's federated timeline under Patient A's grant `grant-a-drx`:

```bash
curl -s -X POST localhost:8300/v1/federated-queries -H 'content-type: application/json' -d '{
  "patient_ref": "pat-a",
  "scope": ["encounters", "medications"],
  "purpose": "Consultation de cardiologie",
  "requested_by": {"organization_ref": "org-hospital-a", "actor_ref": "clin-x"},
  "authorization": {"basis": "patient_access_grant", "ref": "grant-a-drx", "expires_at": "2026-10-24T09:00:00+01:00"}
}'
```

The result is `partial`:

- Hospital A answers with 1 entry, and Hospital B with 2, including Medication A (`MED-COAGULIX`).
- The private practice node is `unavailable` because its DMI is disconnected in the demo data.
- The notice says that missing entries are not evidence of absence.
- `provenance.mocked` is `true`.

Add `"target_organization_refs": ["org-hospital-b"]` to ask Hospital B only. The result is then `complete`.

Other states to show:

| Change to the request | Result |
|---|---|
| Purpose other than the grant's | `200`; every reachable node answers `denied` |
| `authorization.expires_at` in the past | `403 authorization_denied`; no node is asked |
| `target_organization_refs: ["org-hospital-c"]` (still in onboarding) | `400 invalid_request` |
| Missing or malformed fields | `400 invalid_request`, `application/problem+json` |
| Started without a seed (empty registry) | `503 federation_unavailable`: "No Hospital Node is registered." |

Registry states to show:

| Action | Result |
|---|---|
| `DELETE /v1/registry/nodes/node-private-practice`, then the timeline request | `complete`; only Hospitals A and B are asked |
| `PUT /v1/registry/nodes/node-hospital-b` with a new `base_url` | `200`; `registered_at` unchanged, `updated_at` moves |
| `PUT` a second node for `org-hospital-b` | `409 organization_already_registered` |
| `PUT` with `contract_versions: ["2.0"]` | `400`; only hospital-node-federation `1.0` is supported |
| `PUT` with credentials or a query in `base_url` | `400 invalid_request` |
| `GET` or `DELETE` an unknown node | `404 node_not_found` |

The grant expires on 2026-10-24. Because the service uses the real clock, the demo request is refused with `403` after that date unless the fixtures are updated.

## Layout

```text
services/federation/
├── main.py                     # composition root; create_app(clock, registry_seed)
├── registry-seed.demo.json     # fictional demo node registrations
├── domain/                     # query and aggregation rules; node registration rules — stdlib only
├── application/                # FederatePatientQuery and NodeRegistry use cases; HospitalNodeClient and RegistrationStore ports
├── adapters/inbound/http/      # federated query and registry routers, problem+json errors, /health
├── adapters/outbound/
│   ├── hospital_node_contract.py        # wire mapping for hospital-node-federation.v1 (reused by HC-145)
│   ├── in_memory_registration_store.py  # RegistrationStore kept in this process
│   └── simulated_hospital_nodes.py      # SimulatedHospitalNodes (MOCKED)
├── infrastructure/registry_seed.py      # loads FEDERATION_REGISTRY_SEED at startup
└── tests/                      # domain, use cases, seed, simulated nodes, HTTP/contract, layer boundaries
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library.

## How the mock keeps the boundaries

- **The use case knows only the ports.** It never sees files, grants, or records. Replacing `SimulatedHospitalNodes` with an HTTP client for real Nodes (HC-145) changes no domain or application code.
- **Each simulated node reads only its own organization's records file.** It receives the request in the [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) wire format and answers in it. Tests validate every simulated answer against that contract.
- **Nodes enforce the authorization and deny by default.** A patient access grant must be active, unexpired, unrevoked, for the same patient, actor, and purpose, and cover the scope. A synchronization decision must be approved, still valid, name this node's organization as the target, and match the requester, patient, purpose, and scope. The simulated nodes read these from the fictional `access.json` and `governance.json`, standing in for verification with the Governance Node (HC-144).
- **Federation stores nothing.** The merged result exists only for the response.
- **Which nodes are asked comes from the real registry,** not from the demo data. A registered node with no simulation answers `unavailable`.

## Node registry boundaries

- **It routes; it does not approve.** Approving an organization belongs to the Governance Node. Each registration cites the Governance decision it relies on, but nothing can check that reference until a Governance approval API exists (HC-131). The API says `approval.verified: false`, and the list carries a notice saying so.
- **It holds routing data only:** node and organization references, base URL, and contract versions. It holds nothing about patients.
- **One node per organization,** because federated queries target organizations.
- **Compatible nodes only:** a node must answer hospital-node-federation `1.0`.
- **Base URLs** must be absolute http(s) URLs without credentials, query, or fragment, so no secrets end up in the registry.
- **Not production-ready:** registry writes are unauthenticated, and node identity and trust are OPEN. Registrations live in memory because persistence is OPEN.

## Non-responsibilities

It is not a centralized clinical database, does not access Hospital Node tables directly, and does not connect directly to hospital DMI/HIS systems. It cannot grant access; only the Governance-backed basis checked by each node can.

## Contracts

- [`federated-patient-query.v1.yaml`](../../contracts/federation/federated-patient-query.v1.yaml): provided by this service. Implemented with MOCKED nodes (HC-141). Tests check that the demo requests reproduce the contract's `partialTimeline` and `completeHospitalB` examples.
- [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml): called on each Hospital Node. Simulated in process until the Hospital Node implements it.
- [`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml): provided by this service (HC-142). Tests validate every response against it.
- PLANNED: capability discovery (HC-143), Governance verification of authorizations (HC-144), and audit event contracts.
