# Current Implementation Status

Status is based on repository inspection, not product intent. Use the [shared vocabulary](README.md#status-vocabulary). Re-check code, tests, tickets, and ADRs before relying on this snapshot.

## Implemented

- **Repository structure — IMPLEMENTED:** named boundaries exist for apps, instances, services, integrations, contracts, infrastructure, production, IoT, documentation, scripts, and cross-system tests.
- **Documentation — IMPLEMENTED:** canonical product vision, architecture, component boundaries, planning, contribution rules, and status guidance exist.
- **Planning documents — IMPLEMENTED:** backlog, milestones, canonical demo, and dependency diagrams exist as plans only.
- **GitHub governance — IMPLEMENTED:** issue/PR templates, CODEOWNERS placeholder, Dependabot placeholder, and workflow files exist.
- **Workflow behavior — IMPLEMENTED but limited:** project automation exists; CI, lint, tests, and Docker workflows are manual placeholders rather than product validation pipelines.
- **PlatformIO preparation — IMPLEMENTED placeholder:** `platformio.ini` and empty firmware directories exist.
- **Web design system — IMPLEMENTED (D1):** `design-system/` contains Tailwind CSS v4 tokens, base typography, presentational React components (buttons, form fields, cards, tables, badges, alerts, navigation/shell, loading/empty/error states, timeline), explicit demo labelling, and a showcase page ([ADR-0002](decisions/ADR-0002-web-design-system.md)). Build, lint, showcase rendering, and consumption by a throwaway portal outside the repository were checked; no portal in the repository uses it yet, and no automated component tests exist. Mobile reuse is OPEN.
- **Deployment/production preparation — IMPLEMENTED documentation/placeholders:** no deployed runtime or selected provider is implied.

- **AI Services runtime skeleton — VALIDATED (local):** [`services/ai/`](../services/ai/README.md) is a FastAPI service with `GET /health`, framework-free Domain/Application layers, and pytest tests (use case, HTTP, layer boundaries). Its tests, ruff checks, and local `fastapi dev`/`fastapi run` servers were verified. It exposes no real AI capability and is not deployed.

## Not implemented

- **Web products — PLANNED:** Hospital Portal, Governance Portal, and Research Portal contain documentation only. Their technology (React + TypeScript + Vite SPA) is CONFIRMED by [ADR-0001](decisions/ADR-0001-web-frontend-technology.md), but no portal has been scaffolded.
- **Mobile products — PLANNED:** Patient App and Clinician App contain documentation only; no mobile framework or `android/`/`ios/` project exists.
- **Backend runtime strategy — CONFIRMED:** [ADR-0003](decisions/ADR-0003-backend-runtime-strategy.md) selects Python + FastAPI for every Node and service. Only the AI Services skeleton exists so far (see Implemented); no Node or other service runtime has been created.
- **Hospital Node — PLANNED:** no runtime, local API, storage, identity, consent, audit, health endpoint, or Federation implementation.
- **Governance Node — PLANNED:** no runtime, policy engine, authorization, audit persistence, or ledger adapter.
- **DMI Adapter — PLANNED:** its Hospital Node-local boundary exists, but no port, mapping, configuration, fixture, or implementation.
- **Federation Service — PLANNED:** no discovery, node identity, synchronization, query, authorization, or aggregation code.
- **Notification Service — PLANNED:** no provider, transport, event processing, or delivery code.
- **Research Service and Compute-to-Data — PLANNED:** no orchestrator, sandbox, Hospital Node agent, execution, or controlled-output validation.
- **SciAgents Integration — PLANNED:** SciAgents exists externally, but this repository has no connector or contract implementation.
- **AI capabilities — PLANNED:** no AI library, provider, model, real extraction, explanation, or clinical validation code exists. Clinical extraction is MOCKED only (see Mocked behavior).
- **Blockchain / Immutable Audit Ledger — OPTIONAL / PLANNED:** no `AuditLedgerPort`, adapter, simulated ledger, or real ledger exists.
- **Authentication, authorization, RBAC, and organization identity — PLANNED:** no production or demo implementation exists.
- **Persistence and canonical/FHIR model — PLANNED:** no database, ORM, schema, FHIR server, or profile is selected.
- **Communication contracts — PLANNED except one:** the only defined contract is the AI clinical extraction API, [`contracts/api/ai/clinical-extraction.v1.yaml`](../contracts/api/ai/clinical-extraction.v1.yaml) (HC-152). No event, Federation, or message schema exists.
- **Product tests — PLANNED:** test directories are placeholders and contain no product tests.
- **Product deployment — NOT IMPLEMENTED:** no production build, container image, package, hosting configuration, tunnel, or deployment exists.

## Mocked behavior

- **AI clinical extraction — MOCKED (D1):** `POST /v1/clinical-extractions` in [`services/ai/`](../services/ai/README.md) implements the HC-152 contract with a deterministic fixture extractor. It recognises one fictional demo transcript (Patient A) and returns a fixed draft; any other text returns an empty draft. Every response is labelled `provenance.mocked: true` and `review_status: pending_clinician_review`. Its responses are checked against the contract by automated tests. This is not clinical intelligence.

No other product mock exists. Planning documents permit further fictional fixtures and deterministic demo behavior, but those plans are not implementation.

## Validated behavior

Repository documentation links, YAML syntax, and structural consistency may be validated during documentation work. No clinical, security, Federation, AI, research, or deployment capability is VALIDATED.
