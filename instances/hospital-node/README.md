# Hospital Node

## Purpose and status

CONFIRMED autonomous hospital-controlled boundary. Its stack (Python + FastAPI, one process per hospital from one codebase, flat layer layout that keeps `adapters/dmi/`) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-110): a FastAPI app with Clean/Hexagonal layers, pinned dependencies, and tests. Per-hospital configuration loading is IMPLEMENTED at D2 (HC-112). Its only endpoint is `GET /health` (HC-111, IMPLEMENTED at D2). **It holds no clinical data.** The clinical repository and APIs (HC-113 to HC-116) are PLANNED. It is expected to become a separately packaged/containerized instance; container choices remain OPEN.

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
| `storage_dir` | This hospital's local storage directory. A relative path is resolved against the configuration file. Nothing reads or writes it until HC-113. `.storage/` is git-ignored. |
| `notice` | Optional free-text note. |

The node refuses to start if the variable is unset, the file cannot be read, or any field is missing, unknown, or invalid. It never falls back to another hospital's identity.

The fictional demo configurations in [`config/`](config/) match the approved node organizations in [`demo-data/organizations.json`](../../demo-data/organizations.json) and the ports in the Federation [registry seed](../../services/federation/registry-seed.demo.json):

| File | Node | Organization | Port |
|---|---|---|---|
| `hospital-a.demo.json` | `node-hospital-a` | `org-hospital-a` | 8101 |
| `hospital-b.demo.json` | `node-hospital-b` | `org-hospital-b` | 8102 |
| `private-practice.demo.json` | `node-private-practice` | `org-private-practice` | 8104 |

Hospital C is still in onboarding in the demo data and has no node, so it has no configuration; ADR-0003 reserves port 8103 for it. This is demo configuration only: the identity is not authenticated, and it is not a production configuration or secret store.

## Health endpoint (HC-111)

`GET /health` is a liveness check. It returns `200` with the node kind, version, the configured `node_ref` and `organization_ref`, an empty `capabilities` list, and a notice stating that the identity comes from fictional demo configuration, that the instance holds no clinical data, and that it is not a production health check:

```json
{"status": "ok", "node": "hospital-node", "version": "0.1.0", "node_ref": "node-hospital-a", "organization_ref": "org-hospital-a", "capabilities": [], "notice": "Hospital Node runtime skeleton (HC-111, HC-112). ..."}
```

It does not check storage, DMI connectivity, or Federation reachability; none exists yet. Deployment health checks are PLANNED in HC-223. Besides `/health`, only FastAPI's generated `/openapi.json` and `/docs` are served.

## Layout

```text
instances/hospital-node/
├── main.py                     # composition root: loads configuration, builds the FastAPI app
├── config/                     # fictional per-hospital demo configurations
├── domain/                     # NodeIdentity, NodeStatus — stdlib only
├── application/                # get_node_status use case; imports only domain
├── adapters/inbound/http/      # /health router and Pydantic response model
├── infrastructure/             # configuration loading and validation
├── adapters/dmi/               # PLANNED hospital-local DMI Adapter (HC-120+)
├── contracts/                  # reserved for Node-local contract documents
└── tests/                      # app and layer-boundary tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library.

## Responsibilities and owned concepts

- Local clinical integration and canonical/FHIR representation.
- Hospital-specific DMI Adapter boundary at `adapters/dmi/`.
- Local storage and clinical source-data control.
- Consent/authorization enforcement at the local boundary.
- Local audit generation and Federation interface.
- Per-hospital configuration loading and liveness health check (IMPLEMENTED); future local API, authenticated identity/RBAC, and events.

## Communication boundaries

The Node communicates through versioned API, event, and Federation contracts. `contracts/` is reserved for Node-owned local ports; repository-level cross-component contracts live at `/contracts`. Each hospital owns its DMI implementation and configuration.

## Non-responsibilities

The Hospital Node does not own ethics approval, global research approval, company billing, or central blockchain authority. Central services must not access its database or DMI/HIS directly.

## Expected contracts

Each Hospital Node must provide [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) (HC-140): a node descriptor and authorized, scoped patient queries that the node enforces itself. The contract is defined; no Node implements it yet.

PLANNED local clinical API, DMI port, consent/authorization, audit-event, and research-execution contracts. `/health` is Node-local and has no versioned contract.
