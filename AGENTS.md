# Agent Instructions

## Scope

These instructions apply to the entire repository. Keep changes appropriate for a two-day hackathon and within the current validated issue. Before coding, complete the [agent startup checklist](docs/AGENT_STARTUP_CHECKLIST.md).

## Source of truth hierarchy

Resolve conflicts in this order:

1. [Canonical product vision](docs/product/FEDERATED_HEALTHCARE_ECOSYSTEM.md): product scope and invariants.
2. [Technical architecture](docs/architecture.md): technical boundaries.
3. `AGENTS.md`: mandatory coding-agent behavior.
4. [Contribution guide](CONTRIBUTING.md): Git and GitHub workflow.
5. [Planning](docs/planning/backlog.md): sequencing and temporary ticket definitions.
6. [ADRs](docs/decisions/README.md): accepted technical decisions.
7. Component READMEs: local ownership and status only.
8. Production, infrastructure, and IoT documentation: environment-specific guidance.

Surface contradictions rather than guessing. Use the shared [status vocabulary](docs/README.md#status-vocabulary) exactly enough to distinguish decisions, plans, mocks, implementation, and validation.

## Product invariants

- The ecosystem is federated, not one central clinical database.
- Clinical source data remains under the corresponding Hospital Node's control.
- The Governance Node governs authorization and policy; it does not own hospital clinical source data.
- The company platform is not the Governance / Ethics Authority.
- The Patient App consumes authorized views and does not own or directly access hospital databases.
- The Clinician App consumes authorized patient context and does not directly access hospital databases.
- Research uses Compute-to-Data in preference to unrestricted raw dataset downloads.
- AI assists accountable humans and is never autonomous clinical authority.
- SciAgents exists externally and is integrated, not rebuilt.
- each DMI Adapter is local to its Hospital Node.
- Blockchain belongs behind the Governance Node boundary and stores minimized proofs, never medical records.

## Architecture invariants

- Respect Clean / Hexagonal Architecture in every business backend or service.
- Dependencies point inward: `infrastructure/framework -> adapters -> application -> domain`.
- Domain code must not depend on frameworks, databases, ORMs, brokers, external APIs, Docker, cloud libraries, blockchain libraries, or provider-specific AI SDKs.
- Use explicit application-owned ports for external details.
- Do not import another service's infrastructure or persistence internals.
- Do not create speculative microservices, artificial layers, or generic shared dumping-ground folders.
- Prefer pragmatic boundaries suitable for a two-day hackathon.

## Repository boundaries

- `apps/`: named web and mobile user products only.
- `instances/`: autonomous Hospital Node and Governance Node runtimes.
- `services/`: justified AI, Federation, Notification, and Research capabilities.
- `integrations/`: company/platform integrations such as SciAgents; hospital-local systems belong inside their Node.
- `contracts/`: versionable cross-component API, event, federation, and message definitions.
- `infrastructure/`, `production/`, and `iot/`: technical or environment-specific assets after decisions justify them.
- `tests/`: cross-system integration and end-to-end tests.
- `docs/`: durable product, architecture, planning, decisions, and status knowledge.

Do not create a generic backend location, generic `shared/` folders, or speculative packages. Do not scaffold internal application layers until the stack and requirements are known.

## Communication rules

- Cross-component communication must use explicit contracts, ports, APIs, events, or federation interfaces.
- Significant contracts belong under `contracts/` and must be versionable.
- Contracts describe communication, never another component's internal persistence model.
- No shared database tables or direct cross-component SQL access.
- No Patient App or Clinician App database connection.
- No central service may connect directly to every hospital DMI.
- Document new communication patterns and consequential contract changes.

## Implementation-status rules

Before changing or describing a capability, determine whether it is only documented, MOCKED, partially IMPLEMENTED, IMPLEMENTED, or VALIDATED. Inspect the current ticket, actual code, tests, relevant ADRs, and component README. Never infer implementation from product vision, architecture, plans, directory names, or README prose alone. Documentation existence is not feature implementation; build success alone is not runtime or deployment validation.

## Mocking rules

- Demo-first mocks are allowed when the ticket permits them.
- Mock behavior must be explicit and use fictional data only.
- Never describe MOCKED behavior as production-ready, secure, or VALIDATED.
- A mock ledger is not real blockchain persistence.
- Mock federation is not real node-to-node exchange.
- Mock AI is not validated medical intelligence.
- Mock authentication or authorization is not production security.

## AI-specific rules

- Python is CONFIRMED for potential AI components; frameworks, providers, and models remain OPEN until an ADR decides them.
- Keep provider SDKs outside Domain and behind ports/adapters.
- Do not bind business logic directly to one LLM provider.
- AI outputs require provenance, uncertainty handling, and human review appropriate to their use.

## Clinical safety rules

- LLM output is advisory.
- Medication warnings must not rely solely on an LLM; use deterministic rules or validated sources, with AI only as an explanation layer where appropriate.
- Clinical extraction requires clinician review before becoming confirmed clinical data.
- Priority AI must not be the sole mechanism for critical triage.
- Research or AI findings must not silently become clinical truth.
- Never claim diagnosis, prescription authority, medical validation, or clinical safety unless explicitly IMPLEMENTED and VALIDATED.

## Data ownership rules

- Hospital Nodes control clinical source data and local storage.
- The Governance Node controls governance decisions and authorization records.
- The Research Portal manages project workflows subject to governance authorization.
- Mobile applications consume authorized views; they do not acquire raw-data ownership.
- Do not centralize raw clinical data without an explicit, accepted architectural decision consistent with the product vision.

## Governance rules

- Governance / Ethics Authority decisions belong to the Governance Node boundary.
- Company-managed onboarding and research products may submit or display decisions but must not approve their own requests.
- Synchronization and research access require explicit scope, purpose, duration, policy, consent/authority, and audit handling as applicable.

## DMI rules

The DMI Adapter belongs at `instances/hospital-node/adapters/dmi/`:

```text
Legacy DMI / HIS -> Hospital-specific DMI Adapter
                 -> canonical/FHIR representation -> Hospital Node
```

Each hospital may require different implementation, mapping, and configuration. The adapter may be inbound and/or outbound infrastructure around a Hospital Node-owned port. A central service-to-hospital-DMI connection is forbidden.

## SciAgents rules

SciAgents already exists externally. This repository owns only its integration contract, client adapter, authentication boundary, request/response mapping, error handling, provenance, and Research Portal integration. Rebuilding SciAgents internally is forbidden unless a future explicit decision authorizes it.

## Blockchain rules

Blockchain is OPTIONAL and belongs behind a Governance application `AuditLedgerPort`. Allowed proof data may include event IDs, authorization IDs, timestamps, signatures, versions, hashes, and organization identifiers. Never place patient records, diagnoses, prescriptions, lab results, consultation notes, medical images, or raw FHIR resources on-chain. No blockchain library belongs in Domain.

## Research compute-to-data rules

Preferred flow:

```text
research code -> authorized execution environment -> Hospital Node data
              -> controlled result -> researcher
```

Do not replace this with unrestricted export of raw hospital databases to a researcher's machine. Authorization, isolation, output validation, and provenance must remain explicit boundaries.

## Git rules

Follow [CONTRIBUTING.md](CONTRIBUTING.md). Branch from the agreed base using its convention, keep commits focused, and use `type(scope): concise description`. Do not rewrite shared history, include unrelated changes, commit without request, or push without authorization.

## Issue workflow

Use `Backlog -> Ready -> In Progress -> In Review -> Testing -> Done`; use `Blocked` only when progress depends on unresolved input. Self-assign a Ready issue before implementation and keep status current when a remote project exists. Do not create or modify remote issues/projects without explicit authorization.

## Testing rules

Prioritize Domain tests, Application/use-case tests, adapter integration tests, then cross-system/E2E tests. Domain and use cases must run without Docker, real databases, network access, or web servers. Use test doubles at ports. Add no speculative business tests before requirements exist. Validate runtime integration when relevant; passing compilation alone is not validation.

## Documentation rules

- Label statements using the shared status vocabulary where ambiguity is possible.
- Update architecture and component documentation with boundary changes.
- Use ADRs only for actual consequential decisions; do not invent accepted choices.
- Keep global product truth in the product vision, global technical boundaries in architecture, and local ownership in component READMEs.
- Keep relative Markdown links valid and terminology consistent.
- Never claim a feature is complete merely because documentation or a placeholder exists.

## Security and secrets

Never commit credentials, tokens, patient or personal data, production data, populated environment files, private certificates, or real clinical fixtures. Use `.env.example` only for safe variable names required by implemented services. Treat healthcare data as sensitive.

## Out-of-scope discoveries

Record unrelated discoveries as a proposed issue or PR note; do not expand current scope without agreement. Put unresolved, supported architectural questions in [OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md).

## Forbidden actions

Do not invent product requirements or implementation status; adopt an undecided stack; bypass contracts; share databases; centralize hospital data silently; connect central services directly to DMI systems; put raw medical data on blockchain; rebuild SciAgents; grant AI clinical authority; add unjustified services or abstractions; commit secrets or health data; deploy; expose tunnels; silently install privileged software; or modify remote resources without explicit authorization.
