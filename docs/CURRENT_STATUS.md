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

- **AI Services runtime skeleton — VALIDATED (local):** [`services/ai/`](../services/ai/README.md) is a FastAPI service with `GET /health`, framework-free Domain/Application layers, and pytest tests (use case, HTTP, layer boundaries). Its tests, ruff checks, and local `fastapi dev`/`fastapi run` servers were verified. It is not deployed.
- **AI provider port — IMPLEMENTED:** the provider-neutral `AiProvider` port (HC-151) lives in `services/ai/application/`. Adapters: Claude through the Claude Agent SDK, local Ollama, and a deterministic mock, combined by `FallbackAiProvider` ([ADR-0006](decisions/ADR-0006-ai-provider-strategy.md)). Outputs carry provenance and stay pending human review.
- **Real clinical extraction — IMPLEMENTED (D3), live-checked locally, not clinically validated:** in model mode (the default), `POST /v1/clinical-extractions` calls Claude first and the local Ollama model as fallback (HC-153). Items whose evidence quote is not in the source text are dropped; drafts stay pending clinician review; if no provider answers, the API returns `503 extraction_unavailable`. Automated tests use test doubles; opt-in live tests and local end-to-end calls against the real providers passed on the fictional demo transcript. Extraction quality has not been measured with an evaluation set.

## Not implemented

- **Web products — PLANNED:** Hospital Portal, Governance Portal, and Research Portal contain documentation only. Their technology (React + TypeScript + Vite SPA) is CONFIRMED by [ADR-0001](decisions/ADR-0001-web-frontend-technology.md), but no portal has been scaffolded.
- **Mobile products — PLANNED:** Patient App and Clinician App contain documentation only. Flutter + Dart and the Android development path are CONFIRMED by [ADR-0004](decisions/ADR-0004-mobile-technology.md); no dependencies, application code, or generated platform project exists.
- **Backend runtime strategy — CONFIRMED:** [ADR-0003](decisions/ADR-0003-backend-runtime-strategy.md) selects Python + FastAPI for every Node and service. Only the AI Services skeleton exists so far (see Implemented); no Node or other service runtime has been created.
- **Hospital Node — PLANNED:** no runtime, local API, storage, identity, consent, audit, health endpoint, or Federation implementation.
- **Governance Node — PLANNED:** no runtime, policy engine, authorization, audit persistence, or ledger adapter.
- **DMI Adapter — PLANNED:** its Hospital Node-local boundary exists, but no port, mapping, configuration, fixture, or implementation.
- **Federation Service — PLANNED:** no discovery, node identity, synchronization, query, authorization, or aggregation code. Its contracts are defined (HC-140) but not implemented.
- **Notification Service — PLANNED:** no provider, transport, event processing, or delivery code.
- **Research Service and Compute-to-Data — PLANNED:** no orchestrator, sandbox, Hospital Node agent, execution, or controlled-output validation.
- **SciAgents Integration — PLANNED:** SciAgents exists externally. The repository-side contract is defined (see Communication contracts), but no connector exists.
- **Other AI capabilities — PLANNED:** summarization, document review, lab extraction, medication and priority explanations, and any clinical validation of AI output do not exist.
- **Blockchain / Immutable Audit Ledger — OPTIONAL / PLANNED:** no `AuditLedgerPort`, adapter, simulated ledger, or real ledger exists.
- **Authentication, authorization, RBAC, and organization identity — PLANNED:** no production or demo implementation exists.
- **Persistence and canonical/FHIR model — PLANNED:** no database, ORM, schema, FHIR server, or profile is selected.
- **Communication contracts — mostly PLANNED:** three API contracts are defined: AI clinical extraction, [`clinical-extraction.v1.yaml`](../contracts/api/ai/clinical-extraction.v1.yaml) (HC-152); medication safety check, [`medication-safety-check.v1.yaml`](../contracts/api/medication-safety/medication-safety-check.v1.yaml) (HC-160); and SciAgents scientific investigation, [`scientific-investigation.v1.yaml`](../contracts/api/sciagents/scientific-investigation.v1.yaml) (HC-170). Only the clinical extraction contract has an implementation (MOCKED). Two Federation contracts are defined (HC-140): [`hospital-node-federation.v1.yaml`](../contracts/federation/hospital-node-federation.v1.yaml) and [`federated-patient-query.v1.yaml`](../contracts/federation/federated-patient-query.v1.yaml). They have no provider or implementation. No event or message schema exists.
- **Product tests — mostly PLANNED:** only `services/ai/tests/` and the repository [contract tests](../tests/contracts/) exist; `tests/integration/` and `tests/e2e/` are empty placeholders.
- **Product deployment — NOT IMPLEMENTED:** no production build, container image, package, hosting configuration, tunnel, or deployment exists.

## Mocked behavior

- **Canonical demo data — MOCKED (D1):** `demo-data/` holds fictional JSON for three hospitals, a private practice, the Governance / Ethics Authority, three patients, clinicians, encounters, medications, labs, access grants, synchronization and research requests, decisions, audit events, simulated ledger proofs, research jobs, a SciAgents fixture, alerts, and notifications ([ADR-0005](decisions/ADR-0005-canonical-demo-data.md)). `python demo-data/check_fixtures.py` passes. Medicines and the interaction rule are invented and not validated. No product reads the data yet.
- **AI clinical extraction fixture mode — MOCKED (D1):** with `AI_EXTRACTION_MODE=fixture`, `POST /v1/clinical-extractions` in [`services/ai/`](../services/ai/README.md) uses the HC-152 deterministic fixture extractor instead of a model. It recognises one fictional demo transcript (Patient A) and returns a fixed draft; any other text returns an empty draft. Every response is labelled `provenance.mocked: true` and `review_status: pending_clinician_review`. Its responses are checked against the contract by automated tests. This is not clinical intelligence.
- **AI provider mock — MOCKED (D1):** `DeterministicMockAiProvider` (HC-151), used in fixture mode, returns fixed `[MOCK]` templates and never echoes input. It is not AI and not validated intelligence.

No other product mock exists. Planning documents permit further fictional fixtures and deterministic demo behavior, but those plans are not implementation.

## Validated behavior

Repository documentation links, YAML syntax, and structural consistency may be validated during documentation work. No clinical, security, Federation, AI, research, or deployment capability is VALIDATED.
