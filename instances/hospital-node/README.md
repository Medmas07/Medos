# Hospital Node

## Purpose and status

CONFIRMED autonomous hospital-controlled boundary. Its stack (Python + FastAPI, one process per hospital from one codebase, flat layer layout that keeps `adapters/dmi/`) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-110): a FastAPI app with empty Clean/Hexagonal layers, pinned dependencies, and tests. **It exposes no product endpoint and holds no clinical data.** The health endpoint (HC-111), per-hospital configuration for demo hospitals A/B/C (HC-112), and clinical repository and APIs (HC-113 to HC-116) are PLANNED. It is expected to become a separately packaged/containerized instance; container choices remain OPEN.

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

The only route is FastAPI's generated `/openapi.json` (and `/docs`), whose `paths` are empty.

## Layout

```text
instances/hospital-node/
├── main.py                     # composition root: builds the FastAPI app
├── domain/                     # empty — stdlib only
├── application/                # empty — use cases and their ports; imports only domain
├── adapters/inbound/http/      # empty — FastAPI routers and Pydantic models
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
- Future local API, identity/RBAC, events, and health checks.

## Communication boundaries

The Node communicates through versioned API, event, and Federation contracts. `contracts/` is reserved for Node-owned local ports; repository-level cross-component contracts live at `/contracts`. Each hospital owns its DMI implementation and configuration.

## Non-responsibilities

The Hospital Node does not own ethics approval, global research approval, company billing, or central blockchain authority. Central services must not access its database or DMI/HIS directly.

## Expected contracts

PLANNED local clinical API, DMI port, consent/authorization, audit-event, synchronization, Federation, research-execution, and health contracts.
