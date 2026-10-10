# Federation Service

## Purpose and status

Coordination capability for authorized communication among autonomous Nodes. Python + FastAPI per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md).

- **IMPLEMENTED (D2):** a runnable service that serves [`federated-patient-query.v1.yaml`](../../contracts/federation/federated-patient-query.v1.yaml) (HC-141). It asks each approved Hospital Node, merges the answers into a transient timeline, and reports a status for each node.
- **MOCKED:** the Hospital Nodes and the node registry. No Hospital Node runtime exists yet, so each approved organization in [`demo-data/`](../../demo-data/README.md) is simulated in process. **This is not node-to-node exchange and not production security.**
- **PLANNED:** real node registry (HC-142), capability discovery (HC-143), Governance verification of authorizations (HC-144), real node-to-node calls (HC-145), and audit events.

## Running locally

From this directory (POSIX shell; on Windows activate with `.venv\Scripts\activate`):

| Purpose | Command |
|---|---|
| Create environment | `python3 -m venv .venv && . .venv/bin/activate` |
| Install (dev) | `pip install -r requirements-dev.txt` |
| Dev server with reload | `fastapi dev main.py --port 8300` |
| Tests | `pytest` |
| Lint / format check | `ruff check . && ruff format --check .` |
| Production-mode server (preview) | `fastapi run main.py --port 8300` |

`GET /health` reports `"mocked": true` and a notice that the nodes are simulated.

## Demo

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

The grant expires on 2026-10-24. Because the service uses the real clock, the demo request is refused with `403` after that date unless the fixtures are updated.

## Layout

```text
services/federation/
├── main.py                     # composition root; create_app(clock) wires the mock adapters
├── domain/                     # query, entry, node result, aggregation rules — stdlib only
├── application/                # FederatePatientQuery use case; NodeRegistry and HospitalNodeClient ports
├── adapters/inbound/http/      # contract router, problem+json errors, /health
├── adapters/outbound/
│   ├── hospital_node_contract.py    # wire mapping for hospital-node-federation.v1 (reused by HC-145)
│   └── simulated_hospital_nodes.py  # DemoNodeRegistry, SimulatedHospitalNodes (MOCKED)
└── tests/                      # domain, use case, simulated nodes, HTTP/contract, layer boundaries
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library.

## How the mock keeps the boundaries

- **The use case knows only the ports.** It never sees files, grants, or records. Replacing `SimulatedHospitalNodes` with an HTTP client for real Nodes (HC-145) changes no domain or application code.
- **Each simulated node reads only its own organization's records file.** It receives the request in the [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) wire format and answers in it. Tests validate every simulated answer against that contract.
- **Nodes enforce the authorization and deny by default.** A patient access grant must be active, unexpired, unrevoked, for the same patient, actor, and purpose, and cover the scope. A synchronization decision must be approved, still valid, name this node's organization as the target, and match the requester, patient, purpose, and scope. The simulated nodes read these from the fictional `access.json` and `governance.json`, standing in for verification with the Governance Node (HC-144).
- **Federation stores nothing.** The merged result exists only for the response.
- **The registry** is `organizations.json`: approved organizations that run a node. Hospital C is in onboarding and is never asked.

## Non-responsibilities

It is not a centralized clinical database, does not access Hospital Node tables directly, and does not connect directly to hospital DMI/HIS systems. It cannot grant access; only the Governance-backed basis checked by each node can.

## Contracts

- [`federated-patient-query.v1.yaml`](../../contracts/federation/federated-patient-query.v1.yaml): provided by this service. Implemented with MOCKED nodes (HC-141). Tests check that the demo requests reproduce the contract's `partialTimeline` and `completeHospitalB` examples.
- [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml): called on each Hospital Node. Simulated in process until Hospital Nodes implement it.
- PLANNED: node registry (HC-142), Governance verification of authorizations (HC-144), and audit event contracts.
