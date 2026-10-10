# Current Implementation Status

Status is based on repository inspection, not product intent. Use the [shared vocabulary](README.md#status-vocabulary). Re-check code, tests, tickets, and ADRs before relying on this snapshot.

## Implemented

- **Repository structure — IMPLEMENTED:** named boundaries exist for apps, instances, services, integrations, contracts, infrastructure, production, IoT, documentation, scripts, and cross-system tests.
- **Documentation — IMPLEMENTED:** canonical product vision, architecture, component boundaries, planning, contribution rules, and status guidance exist.
- **Planning documents — IMPLEMENTED:** backlog, milestones, canonical demo, and dependency diagrams exist as plans only.
- **GitHub governance — IMPLEMENTED:** issue/PR templates, CODEOWNERS placeholder, Dependabot placeholder, and workflow files exist.
- **Workflow behavior — IMPLEMENTED but limited:** project automation exists; CI, lint, tests, and Docker workflows are manual placeholders rather than product validation pipelines.
- **PlatformIO preparation — IMPLEMENTED placeholder:** `platformio.ini` and empty firmware directories exist.
- **Deployment/production preparation — IMPLEMENTED documentation/placeholders:** no deployed runtime or selected provider is implied.

## Not implemented

- **Web products — PLANNED:** Hospital Portal, Governance Portal, and Research Portal contain documentation only. Their technology (React + TypeScript + Vite SPA) is CONFIRMED by [ADR-0001](decisions/ADR-0001-web-frontend-technology.md), but no portal has been scaffolded.
- **Mobile products — PLANNED:** Patient App and Clinician App contain documentation only; no mobile framework or `android/`/`ios/` project exists.
- **Hospital Node — PLANNED:** no runtime, local API, storage, identity, consent, audit, health endpoint, or Federation implementation.
- **Governance Node — PLANNED:** no runtime, policy engine, authorization, audit persistence, or ledger adapter.
- **DMI Adapter — PLANNED:** its Hospital Node-local boundary exists, but no port, mapping, configuration, fixture, or implementation.
- **Federation Service — PLANNED:** no discovery, node identity, synchronization, query, authorization, or aggregation code.
- **Notification Service — PLANNED:** no provider, transport, event processing, or delivery code.
- **Research Service and Compute-to-Data — PLANNED:** no orchestrator, sandbox, Hospital Node agent, execution, or controlled-output validation.
- **SciAgents Integration — PLANNED:** SciAgents exists externally, but this repository has no connector or contract implementation.
- **AI Services — PLANNED:** Python is CONFIRMED, but no AI framework, provider, model, endpoint, extraction, or clinical validation code exists.
- **Blockchain / Immutable Audit Ledger — OPTIONAL / PLANNED:** no `AuditLedgerPort`, adapter, simulated ledger, or real ledger exists.
- **Authentication, authorization, RBAC, and organization identity — PLANNED:** no production or demo implementation exists.
- **Persistence and canonical/FHIR model — PLANNED:** no database, ORM, schema, FHIR server, or profile is selected.
- **Communication contracts — PLANNED:** directories exist, but no OpenAPI, event, Federation, or message schemas are defined.
- **Product tests — PLANNED:** test directories are placeholders and contain no product tests.
- **Product deployment — NOT IMPLEMENTED:** no production build, container image, package, hosting configuration, tunnel, or deployment exists.

## Mocked behavior

No product mock implementation currently exists. Planning documents permit future fictional fixtures and deterministic demo behavior, but those plans are not implementation.

## Validated behavior

Repository documentation links, YAML syntax, and structural consistency may be validated during documentation work. No clinical, security, Federation, AI, research, or deployment capability is VALIDATED.
