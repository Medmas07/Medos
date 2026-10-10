# Federation Service

## Purpose and status

Coordination capability for authorized communication among autonomous Nodes. Python + FastAPI per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md).

- **IMPLEMENTED (D2):**
  - the federated patient query, [`federated-patient-query.v1.yaml`](../../contracts/federation/federated-patient-query.v1.yaml) (HC-141). It asks each registered Hospital Node, merges the answers into a transient timeline, and reports a status for each node.
  - the node registry, [`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml) (HC-142): register, update, list, get, and remove nodes. Federated queries ask the nodes listed there. It is kept in memory, and its Governance approval references are **not verified**.
  - temporary sync authorization (HC-144): before any node is asked under a `synchronization_decision`, the service checks it with the Governance Node over real HTTP ([`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml)), then asks only the organizations Governance authorizes. No Governance Node exists yet, so live sync-basis queries return `503` and ask no node. The authorized path is covered by tests only.
  - real node-to-node communication (HC-145), the default: each registered node is asked over HTTP at its registered `base_url` (`POST /v1/federation/queries` of [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml)), in parallel, with a 3-second timeout. Answers are parsed strictly. No Hospital Node serves that endpoint yet, so live queries report every node `unavailable`. The successful path is covered by tests only.
  - capability discovery (HC-143): on request, the service calls each registered node's `GET /v1/federation/node` over real HTTP and keeps the latest result per node. No Hospital Node serves that endpoint yet, so live checks report `no_federation_interface` or `unreachable`. The successful path is covered by tests only.
- **MOCKED, opt-in only:** `FEDERATION_NODES=simulated` replaces the HTTP calls with HC-141's simulated Hospital Nodes, built from [`demo-data/`](../../demo-data/README.md), so the Patient A demo works before real nodes exist. `/health` and every result say `mocked: true` in that mode. **That mode is not node-to-node exchange and not production security.**
- **PLANNED:** using discovered capabilities when choosing which nodes to ask, Governance verification of patient access grants and registry approvals (HC-131), node-side verification of authorizations, the Hospital Node side of the Federation interface, persistent registry storage, service authentication, authentication of registry writes, and audit events.

## Running locally

From this directory (POSIX shell; on Windows activate with `.venv\Scripts\activate`):

| Purpose | Command |
|---|---|
| Create environment | `python3 -m venv .venv && . .venv/bin/activate` |
| Install (dev) | `pip install -r requirements-dev.txt` |
| Dev server with reload, demo nodes registered, real HTTP to nodes | `FEDERATION_REGISTRY_SEED=registry-seed.demo.json fastapi dev main.py --port 8300` |
| Same, with simulated (MOCKED) nodes for the Patient A demo | `FEDERATION_NODES=simulated FEDERATION_REGISTRY_SEED=registry-seed.demo.json fastapi dev main.py --port 8300` |
| Tests | `pytest` |
| Lint / format check | `ruff check . && ruff format --check .` |
| Production-mode server (preview), empty registry | `fastapi run main.py --port 8300` |

`GET /health` reports `"nodes": "http"` or `"simulated"`, `mocked` (true only for simulated nodes), and a notice. `FEDERATION_NODES` accepts only `http` (default) and `simulated`; any other value stops startup.

**The registry starts empty.** Nodes are registered through the API or, at startup, from the JSON file named by `FEDERATION_REGISTRY_SEED`. Seed entries go through the same validation as the API, and an invalid seed stops startup. [`registry-seed.demo.json`](registry-seed.demo.json) registers the three demo nodes: Hospital A, Hospital B, and the private practice. Hospital C is in onboarding and is not registered. Because the registry is in memory, registrations made through the API are lost on restart.

## Demo

**Real mode (default).** Start the Hospital Node runtime for Hospital A (`HOSPITAL_NODE_CONFIG=config/hospital-a.demo.json fastapi run main.py --port 8101` in [`instances/hospital-node/`](../../instances/hospital-node/README.md)) and this service with the demo seed. The timeline request below is `partial`, with every node `unavailable`: Hospital A's runtime answers `404` because it has no Federation endpoint yet, and nothing listens on 8102 or 8104. `provenance.mocked` is `false`.

**Simulated mode.** Add `FEDERATION_NODES=simulated` for the Patient A walkthrough below. The registry lists the three demo nodes, each with `approval.verified: false`:

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
| `authorization.basis: "synchronization_decision"` with a valid `expires_at` | `503`: the Governance Node could not be reached, and no node was asked (nothing runs on port 8200 yet) |
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

Capability discovery (real HTTP; start the Hospital Node runtime with `fastapi run main.py --port 8101` in [`instances/hospital-node/`](../../instances/hospital-node/README.md) to show a reachable node):

| Action | Result |
|---|---|
| `GET /v1/registry/nodes/node-hospital-a/capabilities` before any check | `not_checked`, `checked_at: null` |
| `POST /v1/registry/discovery` | Hospital A: `no_federation_interface` (the runtime answers `404`; it has no Federation endpoint yet). Hospital B and the private practice: `unreachable` (nothing listens on 8102 or 8104). |
| `POST /v1/registry/nodes/{node_ref}/capabilities` | Checks one node now and returns the result |
| `PUT` a new `base_url` for a checked node | Its result returns to `not_checked` |

A node that serves the endpoint gets `discovered` with its reported status, contract versions, scopes, and `mocked` flag. `incompatible` means it answers no supported version. `identity_mismatch` means it names another node or organization, and its claims are discarded. `invalid_response` means the answer is not a valid descriptor.

The grant expires on 2026-10-24. Because the service uses the real clock, the demo request is refused with `403` after that date unless the fixtures are updated.

## Layout

```text
services/federation/
├── main.py                     # composition root; create_app(clock, registry_seed)
├── registry-seed.demo.json     # fictional demo node registrations
├── domain/                     # query, aggregation, registration, discovery, and sync authorization rules — stdlib only
├── application/                # FederatePatientQuery, NodeRegistry, DiscoverNodeCapabilities; their ports
├── adapters/inbound/http/      # federated query, registry, and discovery routers; problem+json errors; /health
├── adapters/outbound/
│   ├── hospital_node_contract.py        # strict wire mapping for hospital-node-federation.v1
│   ├── http_hospital_node_client.py     # real HTTP client for POST /v1/federation/queries
│   ├── http_node_descriptor_client.py   # real HTTP client for GET /v1/federation/node
│   ├── http_sync_authorization_checker.py  # real HTTP client for the Governance check
│   ├── in_memory_discovery_store.py     # latest discovery result per node
│   ├── in_memory_registration_store.py  # RegistrationStore kept in this process
│   └── simulated_hospital_nodes.py      # SimulatedHospitalNodes (MOCKED, FEDERATION_NODES=simulated)
├── infrastructure/registry_seed.py      # loads FEDERATION_REGISTRY_SEED at startup
└── tests/                      # domain, use cases, seed, simulated nodes, HTTP client, HTTP/contract, layer boundaries
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library.

## How the simulated mode keeps the boundaries

- **The use case knows only the ports.** It never sees files, grants, or records. Switching between `SimulatedHospitalNodes` and `HttpHospitalNodeClient` changes no domain or application code.
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

## Capability discovery boundaries

- **Real calls, no mock.** Discovery uses `HttpNodeDescriptorClient` against each node's registered `base_url`, with a 2-second timeout and no redirects. Network test doubles exist only in `tests/`.
- **Self-reported, not verified.** Capabilities are what the node said at `checked_at`. A node may report `mocked: true`, and that is passed through.
- **A failed check is not "no data".** Every result carries an `outcome`, and the list carries a notice saying so.
- **Identity is checked.** If the node at a URL names another node or organization, the result is `identity_mismatch` and its claims are discarded. Without node authentication (OPEN), this catches misrouting, not impersonation.
- **Strict parsing.** Anything outside the contract's `NodeDescriptor` is `invalid_response`, including extra fields such as patient counts.
- **On request only.** Discovery runs when asked, and results are kept in memory. Federated queries do not use capabilities yet.

## Node-to-node communication boundaries

- **Real calls, only to registered nodes.** `HttpHospitalNodeClient` posts the query to the `base_url` the node has in the registry. It uses no other address and never reads a node's database or DMI.
- **Status mapping.** `403` → `denied`. A timeout → `timeout`. A connection error, `404`, `503`, another status, a redirect, or non-JSON → `unavailable`.
- **Strict answers.** The answer is parsed with models mirroring the contract (`extra="forbid"`). An answer is rejected, and the node reported `unavailable`, if it has unknown fields (for example a patient name), is about another query, patient, or node, contains an entry held by another node, or contains an entry outside the requested scope. Nothing from a rejected answer reaches the result.
- **Honest provenance.** A federated result is `mocked: true` when any node said it answered from fixtures, as the contract requires. Real HTTP does not by itself mean real data.
- **Parallel, bounded.** Nodes are asked in parallel. A slow node times out without hiding the others.
- **Not production security.** There is no mutual TLS or service authentication; node identity and trust remain OPEN.

## Temporary sync authorization boundaries

- **Governance decides; Federation enforces.** The service never approves, extends, or widens a synchronization. It asks the Governance Node at `FEDERATION_GOVERNANCE_URL` (default `http://localhost:8200`, the ADR-0003 port) whether the decision authorizes this requester, patient, scope, and purpose now.
- **No node is asked unless Governance confirms.** Federation answers `403` with Governance's reason when it denies. It answers `503` when Governance is unreachable, times out (2 s), redirects, or answers outside the contract, including an answer about a different decision.
- **Only authorized targets.** An authorized query goes only to the organizations Governance names. Requested targets outside them get `403`. This replaces asking every registered node.
- **Never widened.** If Governance's "authorized" answer has already expired, or its scope does not cover the request, Federation refuses anyway.
- **Nodes still decide.** Each node enforces the authorization again. The simulated nodes know only the decisions in `demo-data/`, so a decision created at runtime, such as step 20's approval of `sync-001`, is still denied by the simulated node.
- **Unchanged for patient access grants.** They are patient-issued and are not sent to Governance in this version.
- **Not production security.** There is no service authentication and no signed token; both are OPEN.

## Non-responsibilities

It is not a centralized clinical database, does not access Hospital Node tables directly, and does not connect directly to hospital DMI/HIS systems. It cannot grant access; only the Governance-backed basis checked by each node can.

## Contracts

- [`federated-patient-query.v1.yaml`](../../contracts/federation/federated-patient-query.v1.yaml): provided by this service. Implemented with MOCKED nodes (HC-141). Tests check that the demo requests reproduce the contract's `partialTimeline` and `completeHospitalB` examples.
- [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml): called on each Hospital Node. Simulated in process until the Hospital Node implements it.
- [`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml) 1.1: provided by this service. Registry (HC-142) and capability discovery (HC-143). Tests validate every response against it.
- [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) `GET /v1/federation/node`: called over real HTTP by capability discovery.
- [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml): provided by the Governance Node, called by this service for every synchronization-decision query (HC-144). Tests drive the client with the contract's own examples.
- PLANNED: Governance verification of patient access grants, and audit event contracts.
