# ADR-0003: Backend runtime strategy for Nodes and company services

## Status

Accepted — 2026-10-10, through review of HC-003 ([#26](https://github.com/Medmas07/Hackcure_hackathon/issues/26)).

## Context

The repository plans several server-side runtimes:

- **Autonomous instances:** the [Hospital Node](../../instances/hospital-node/README.md) and the [Governance Node](../../instances/governance-node/README.md).
- **Company services:** [Federation](../../services/federation/README.md), [Research](../../services/research/README.md), and [Notifications](../../services/notifications/README.md).
- **[AI Services](../../services/ai/README.md):** Python is already CONFIRMED.
- **[SciAgents Integration](../../integrations/sciagents/README.md):** a client adapter for an external system.

All of them were PLANNED with no runtime, and the runtime/framework choice was listed in [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md). The runtime skeletons HC-110 (Hospital Node), HC-130 (Governance Node), and HC-150 (AI) are blocked on this decision, and so are the HC-111 to HC-116 and HC-131 to HC-136 APIs and the HC-220 to HC-227 packaging and deployment tickets.

Constraints that drive the choice:

- **Two-day hackathon:** the team should know as few backend languages as possible, setup should be fast, and nothing should depend on paid services.
- **Python is CONFIRMED for AI.** Compute-to-Data also points to Python: the product vision describes a Python notebook environment and a Python research API (`health.query(...)`, `experiment.run(...)`), and the hospital-side research execution agent (HC-183) runs that code inside the Hospital Node boundary.
- **Clean / Hexagonal Architecture is mandatory.** The framework must be a delivery detail that stays out of Domain and Application.
- **Autonomous trust boundaries:** each Hospital Node and the Governance Node are separately deployable and expected to be containerized (HC-220, HC-224). The demo needs several Hospital Nodes (A, B, C) with separate data.
- **Explicit, versionable contracts** under `contracts/`. The web portals are React + TypeScript SPAs (ADR-0001, from HC-001 [#24](https://github.com/Medmas07/Hackcure_hackathon/issues/24)) and need typed API clients.
- **No generic backend, shared database, or speculative microservices.**
- **The DMI Adapter path `instances/hospital-node/adapters/dmi/` is CONFIRMED** by the product vision and architecture, so the code layout must keep it.

## Decision

### Language and framework

| Concern | Choice |
|---|---|
| Language | Python, minimum 3.12 (the evidence below ran on 3.14) |
| HTTP framework (inbound adapter only) | FastAPI (0.136.x at time of decision), installed as `fastapi[standard]` |
| ASGI server | Uvicorn, started by the FastAPI CLI (`fastapi dev` / `fastapi run`) |
| HTTP/config DTO validation | Pydantic (bundled with FastAPI), **in adapters and infrastructure only** |
| Domain/Application modelling | Standard library (`dataclasses`, `enum`, `typing.Protocol` for ports); no framework imports |
| Environment | `python -m venv .venv`, one virtual environment per runtime |
| Dependencies | Per-runtime `requirements.txt` (runtime) and `requirements-dev.txt` (`-r requirements.txt` plus dev tools), with **exact `==` pins** |
| Tests | pytest |
| Lint and format | Ruff (`ruff check`, `ruff format`) |
| Tool configuration | Per-runtime `pyproject.toml` that holds only `[tool.pytest.ini_options]` and `[tool.ruff]` |

This applies to every backend runtime: Hospital Node, Governance Node, Federation, Research, Notifications, AI Services, and any process the SciAgents Integration needs. There is **one backend language**. The only TypeScript in the repository is the web clients.

### Deployable units

Each bounded context is its own Python project with its own dependencies. Projects do not import each other's code. They communicate only through contracts (HTTP APIs, events, or Federation interfaces).

| Runtime | Location | Process model | Created by |
|---|---|---|---|
| Hospital Node | `instances/hospital-node/` | One codebase, **one process per hospital**. Demo hospitals A/B/C run as separate instances of the same code with separate configuration and separate local storage (HC-112). | HC-110 |
| Governance Node | `instances/governance-node/` | One process. | HC-130 |
| AI Services | `services/ai/` | One process. | HC-150 |
| Federation Service | `services/federation/` | One process, created only when its first runtime ticket needs one. | First Federation runtime ticket (e.g. HC-141) |
| Research Service | `services/research/` | One process, created only when needed. | First Research runtime ticket (e.g. HC-181/HC-182) |
| Notification Service | `services/notifications/` | One process, created only when needed. | HC-202 |
| SciAgents Integration | `integrations/sciagents/` | Python client adapter. HC-171 decides whether it is code inside the Research Service or a separate process. | HC-171 |

Runtimes with no ticket get no skeleton. Company services are **not** merged into a generic "company backend", because that would create the shared dumping ground the architecture forbids. A bounded context also must not host another context's endpoints to save time.

Suggested fixed local ports, so the whole ecosystem can run at once next to the web portals (5173–5175):

| Runtime | Port |
|---|---|
| Hospital Node A / B / C | 8101 / 8102 / 8103 |
| Governance Node | 8200 |
| Federation Service | 8300 |
| Research Service | 8400 |
| Notification Service | 8500 |
| AI Services | 8600 |

### Code layout inside a runtime

The runtime directory is the project root. Each layer is a top-level Python package directly inside it. This flat layout keeps `instances/hospital-node/adapters/dmi/` valid as the Python package `adapters.dmi`. Because every runtime has its own virtual environment, generic package names such as `domain` do not collide.

```text
instances/hospital-node/          # same shape for every runtime
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml                # pytest + ruff config only
├── main.py                       # composition root: builds the FastAPI app, wires adapters into use cases
├── domain/                       # entities, value objects, rules — stdlib only
├── application/                  # use cases and the ports they own (typing.Protocol)
├── adapters/
│   ├── inbound/http/             # FastAPI routers + Pydantic request/response models
│   ├── outbound/...              # persistence, other-context clients, providers
│   └── dmi/                      # Hospital Node only — CONFIRMED location
├── infrastructure/               # configuration loading, logging — only when needed
└── tests/
```

Create only the directories a ticket needs. Dependency rules for this layout:

- `domain/` imports nothing outside the standard library and `domain`.
- `application/` imports only `domain`, `application`, and the standard library.
- FastAPI, Pydantic, database drivers, HTTP clients, provider SDKs, and blockchain libraries may only be imported from `adapters/`, `infrastructure/`, or `main.py`.
- Routes translate HTTP to use-case calls and back. Business rules do not live in routes.

The node-owned [`instances/hospital-node/contracts/`](../../instances/hospital-node/contracts/README.md) stays reserved for Node-local contract documents. Python ports live in `application/`, next to the use cases that own them.

### Commands

From inside a runtime directory (POSIX shell; on Windows, activate with `.venv\Scripts\activate`):

| Purpose | Command |
|---|---|
| Create environment | `python3 -m venv .venv && . .venv/bin/activate` |
| Install (dev) | `pip install -r requirements-dev.txt` |
| Dev server with reload | `fastapi dev main.py --port <port>` |
| Tests | `pytest` |
| Lint / format check | `ruff check . && ruff format --check .` |
| Production-mode server (preview) | `fastapi run main.py --port <port>` |

Every runtime exposes its OpenAPI document at `/openapi.json`. Use it as a check against the hand-owned contracts under `contracts/api/` and to generate TypeScript client types for the portals. The generated document does not replace the versioned contract.

### Evidence

On 2026-10-10, two throwaway projects were built **outside the repository** on Python 3.14.8 with `fastapi[standard]==0.136.1` (resolved Starlette 1.7.0, Pydantic 2.14.0, Uvicorn 0.54.0), `pytest==8.4.2`, and `ruff==0.14.0`. The second project used the flat layout and requirements files described above, plus an `adapters/dmi/` directory. In each project:

- a stdlib-only domain object and use case were tested without FastAPI (pytest passed);
- a FastAPI route delegating to that use case was tested through `TestClient` (passed);
- `ruff check` and `ruff format --check` passed;
- `fastapi dev` (with reload) and `fastapi run` both served `/health` and `/openapi.json`;
- `grep` confirmed that `domain/` and `application/` contained no `fastapi`, `pydantic`, or `starlette` import.

This validates the toolchain and layout only. No runtime was implemented in the repository. The probe showed a harmless Starlette deprecation warning recommending `httpx2` for `TestClient`. HC-110 can choose the test HTTP client.

## Alternatives considered

- **TypeScript + NestJS for Nodes and company services, Python for AI:** same language as the web portals, and the framework gives structure out of the box. Rejected because it forces the team to work in two backend languages during a two-day event. It also splits Compute-to-Data, where the Hospital Node runs Python research code, across two stacks. NestJS decorators and modules make it easy to let the framework leak into Domain.
- **TypeScript + Fastify or Express, Python for AI:** lighter than NestJS, but it has the same two-language cost.
- **Go or Java/Spring:** good runtime properties for packaged Nodes, but slower to build with in a hackathon. No backend code exists in either language, and the AI side would still be Python.
- **Flask or Django instead of FastAPI:** Django's ORM-centred model pulls persistence into the core and brings far more than the Nodes need. Flask lacks built-in typed request validation and OpenAPI generation, which the contract-first approach relies on.
- **One combined company backend hosting Federation, Research, and Notifications:** fewer processes, but it is the generic backend the architecture and AGENTS.md forbid, and it would blur ownership between bounded contexts.
- **`uv` or Poetry for dependency management:** both give real lockfiles and faster installs. Not adopted because they add a tool that every contributor must install, and they were not available on the machine used for validation. Exact pins in requirements files are enough for D0–D2. A later ADR may adopt `uv`.
- **`src/` layout with an installable package:** the usual Python packaging layout, but it would move the CONFIRMED `instances/hospital-node/adapters/dmi/` path under `src/<package>/`. The Nodes are deployed as applications, not published as libraries, so being installable adds nothing.

## Consequences

### Positive

- One backend language and one set of commands for every runtime. Contributors can move between the Nodes, services, and AI.
- The Hospital Node can host the Python Compute-to-Data execution agent and use Python FHIR/clinical libraries without a cross-language bridge, if later tickets justify them.
- FastAPI's generated OpenAPI helps keep the TypeScript portals aligned with the `contracts/` definitions.
- Each runtime is a self-contained directory with its own dependencies, which suits per-Node containerization (HC-220, HC-224).
- Unblocks HC-110, HC-130, HC-150 and the tickets that depend on them.

### Negative

- No code sharing between the TypeScript portals and the backends. Types cross the boundary only through contracts and generated clients.
- Python has no compile-time enforcement of the layer rules. Import discipline relies on review until a check (for example `import-linter` or a simple grep in CI) is added.
- Exact pins in requirements files fix direct dependencies only, not transitive ones. Builds are less reproducible than with a lockfile.
- Several processes must be started to run the full ecosystem locally. A run script or container composition becomes useful once two or more runtimes exist.
- FastAPI, Starlette, and Pydantic change quickly. The versions above are a snapshot. Each runtime pins its own.

## Follow-up

- **HC-110 / HC-130 / HC-150:** create each runtime with the layout and commands above, pin dependencies, and add the first framework-free Domain/Application tests.
- **HC-112:** define how one Hospital Node codebase loads per-hospital configuration (node ID, port, storage location) for demo hospitals A/B/C.
- **HC-150:** move AI dependencies into `services/ai/requirements*.txt` and retire or redirect the root [`requirements.txt`](../../requirements.txt) placeholder.
- **Not decided here, left to their own ADRs or tickets:** persistence and ORM per bounded context, FHIR strategy and libraries, authentication and Node identity, Federation transport, event/broker technology, container runtime and images, hosting, and AI provider/model.
- **Boundary enforcement:** add an automated import-direction check for `domain/` and `application/` once the first runtime exists.
- **After the first runtime exists:** replace the placeholder lint/test CI workflows with real `pip install -r requirements-dev.txt`, `ruff`, and `pytest` steps.
