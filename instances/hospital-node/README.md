# Hospital Node

## Purpose and status

CONFIRMED autonomous hospital-controlled boundary. Its stack (Python + FastAPI, one process per hospital from one codebase, flat layer layout that keeps `adapters/dmi/`) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-110): a FastAPI app with Clean/Hexagonal layers, pinned dependencies, and tests. Its only endpoint is `GET /health` (HC-111, IMPLEMENTED at D2). **It holds no clinical data.** Per-hospital configuration for demo hospitals A/B/C (HC-112), and clinical repository and APIs (HC-113 to HC-116) are PLANNED. It is expected to become a separately packaged/containerized instance; container choices remain OPEN.

## Running locally

From this directory (POSIX shell; on Windows activate with `.venv\Scripts\activate`). Until HC-112 adds per-hospital configuration, every instance is identical; port 8101 is Hospital Node A's suggested port.

| Purpose | Command |
|---|---|
| Create environment | `python3 -m venv .venv && . .venv/bin/activate` |
| Install (dev) | `pip install -r requirements-dev.txt` |
| Dev server with reload | `fastapi dev main.py --port 8101` |
| Tests | `pytest` |
| Lint / format check | `ruff check . && ruff format --check .` |
| Production-mode server (preview) | `fastapi run main.py --port 8101` |

## Health endpoint (HC-111)

`GET /health` is a liveness check. It returns `200` with the node kind, version, an empty `capabilities` list, and a notice stating that the instance holds no clinical data, has no hospital identity yet (HC-112), and is not a production health check:

```json
{"status": "ok", "node": "hospital-node", "version": "0.1.0", "capabilities": [], "notice": "Hospital Node runtime skeleton (HC-111). ..."}
```

It does not check storage, DMI connectivity, or Federation reachability; none exists yet. Deployment health checks are PLANNED in HC-223. Besides `/health`, only FastAPI's generated `/openapi.json` and `/docs` are served.

## Layout

```text
instances/hospital-node/
├── main.py                     # composition root: builds the FastAPI app
├── domain/                     # NodeStatus — stdlib only
├── application/                # get_node_status use case; imports only domain
├── adapters/inbound/http/      # /health router and Pydantic response model
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
- Liveness health check (IMPLEMENTED); future local API, identity/RBAC, and events.

## Communication boundaries

The Node communicates through versioned API, event, and Federation contracts. `contracts/` is reserved for Node-owned local ports; repository-level cross-component contracts live at `/contracts`. Each hospital owns its DMI implementation and configuration.

## Non-responsibilities

The Hospital Node does not own ethics approval, global research approval, company billing, or central blockchain authority. Central services must not access its database or DMI/HIS directly.

## Expected contracts

Each Hospital Node must provide [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) (HC-140): a node descriptor and authorized, scoped patient queries that the node enforces itself. The contract is defined; no Node implements it yet.

PLANNED local clinical API, DMI port, consent/authorization, audit-event, and research-execution contracts. `/health` is Node-local and has no versioned contract.
