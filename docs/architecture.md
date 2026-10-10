# Architecture

This document uses the shared [status vocabulary](README.md#status-vocabulary). The [canonical product vision](product/FEDERATED_HEALTHCARE_ECOSYSTEM.md) takes precedence for product scope.

## 1. Architecture status

The federated model, trust boundaries, local data control, Clean / Hexagonal dependency rule, contract-based communication, local DMI placement, Governance-owned authorization, external SciAgents Integration, and advisory AI role are CONFIRMED constraints. The web portal technology is CONFIRMED by [ADR-0001](decisions/ADR-0001-web-frontend-technology.md), the web design-system location and styling by [ADR-0002](decisions/ADR-0002-web-design-system.md), the backend runtime strategy by [ADR-0003](decisions/ADR-0003-backend-runtime-strategy.md), and the mobile technology and Android development path by [ADR-0004](decisions/ADR-0004-mobile-technology.md). Other runtime stacks, databases, protocols, hosting, providers, and concrete implementations remain OPEN. Most capabilities below are PLANNED, not implemented.

## 2. Product context

The ecosystem connects hospitals, patients, clinicians, researchers, company-managed product surfaces, and an independent Governance / Ethics Authority. Hospital Nodes retain clinical source data; authorized views and controlled computation cross boundaries without assuming unrestricted central replication.

## 3. System boundaries

- User products: Hospital Portal, Governance Portal, Research Portal, Patient App, Clinician App.
- Autonomous instances: Hospital Node and Governance Node.
- Supporting capabilities: AI Services, Federation Service, Notification Service, Research Service.
- External boundaries: SciAgents Integration and future third-party adapters.
- Communication definitions: repository-level `contracts/`.
- Web presentation foundation: `design-system/`, consumed by the web portals as a local package ([ADR-0002](decisions/ADR-0002-web-design-system.md)). It contains no domain logic or data access.
- Demo data: `demo-data/`, the canonical fictional dataset read by products and future mock APIs ([ADR-0005](decisions/ADR-0005-canonical-demo-data.md)). Records are split by holding organization; it is neither a contract nor a central clinical database.

No generic backend, shared database, or shared dumping-ground component exists.

## 4. Trust boundaries

```text
Company infrastructure != Governance / Ethics Authority
Hospital A            != Hospital B
Researcher            != Hospital data owner
Patient App           != Hospital database
Clinician App         != Hospital database
AI system             != Clinical authority
```

Every crossing requires explicit identity, authorization, scope, minimization, and audit as applicable.

## 5. Bounded contexts

### Hospital Node

CONFIRMED autonomous hospital-controlled boundary for local clinical integration, storage, consent enforcement, audit generation, DMI Adapter ownership, and federation interfaces. Its runtime is PLANNED.

### Governance Node

CONFIRMED Governance / Ethics Authority boundary for hospital approval, synchronization and research authorization, policy evaluation, governance audit, and OPTIONAL Immutable Audit Ledger integration. It does not own hospital clinical databases. Its runtime is PLANNED.

### Hospital Portal

PLANNED company-managed web portal for onboarding submissions, questionnaire, review status, and Node package access. It does not make governance decisions.

### Governance Portal

PLANNED web interface operated conceptually by the Governance / Ethics Authority for review, authorization, audit exploration, and proof verification.

### Research Portal

PLANNED company-managed web product for research projects, access requests, a Colab-like interface, Compute-to-Data status, controlled results, and SciAgents access.

### Patient App

PLANNED mobile product consuming authorized federated views and managing access/consent interactions. It never connects directly to hospital persistence.

### Clinician App

PLANNED mobile product consuming authorized patient context for consultation and safety workflows. AI output remains advisory and clinician-reviewed.

### AI Services

Python is CONFIRMED. Extraction, summarization, document review, medication explanations, prioritization explanations, and research assistance are PLANNED. Frameworks, providers, and models are OPEN.

### Federation

PLANNED coordination for node discovery, authorization, cross-node queries, synchronization, aggregation, failures, and audit. It must not become a central clinical database.

### Notifications

PLANNED delivery of authorized patient, clinician, researcher, hospital, and governance notifications. Providers and protocols are OPEN.

### SciAgents Integration

SciAgents is an existing external system. This repository's PLANNED responsibility is the integration contract, adapter, authentication boundary, mapping, error handling, provenance, and Research Portal connection—not SciAgents implementation. The repository-side [investigation contract](../contracts/api/sciagents/scientific-investigation.v1.yaml) (HC-170) is defined; it accepts only questions and controlled-result summaries, never raw clinical data, and marks results as not for clinical decisions.

## 6. Hospital Node internal boundary

A future Hospital Node may contain application/domain logic surrounded by local API, identity/RBAC, persistence, DMI, Federation, audit, and event adapters. Dependencies point inward:

```text
infrastructure / framework -> adapters -> application -> domain
```

Domain remains independent of frameworks, databases, blockchain, AI providers, Docker, and cloud services.

## 7. DMI adapter boundary

```text
Legacy DMI / HIS -> Hospital-specific DMI Adapter
                 -> Hospital Node canonical clinical model
                 -> FHIR / internal clinical representation
```

The DMI Adapter is PLANNED at `instances/hospital-node/adapters/dmi/`. Only the corresponding Hospital Node owns its implementation, mappings, and configuration. A central service connecting directly to every hospital DMI is forbidden.

## 8. Governance and authorization

The company may operate product surfaces but is not the Governance / Ethics Authority. Hospital approval, synchronization authorization, research authorization, and governance policies belong to the Governance Node. Authorization should eventually encode identity, purpose, scope, duration, policy, and consent/legal authority, with auditable decisions.

## 9. Blockchain / immutable ledger boundary

```text
Governance Application -> AuditLedgerPort <- Blockchain Adapter
                                           -> Permissioned Immutable Audit Ledger
```

Ledger integration is OPTIONAL / PLANNED and belongs inside Governance. It may anchor minimized IDs, hashes, timestamps, versions, signatures, and organization identifiers. Patient records, diagnoses, prescriptions, lab results, consultation notes, images, and raw FHIR resources are forbidden on-chain. Blockchain is never the clinical database.

## 10. Patient access and consent

Patient access grants, revocation, delegation, and restriction/erasure request experiences are PLANNED. Authorized views do not transfer source-data ownership. Consent is not a substitute for legal authority, policy, identity, or technical authorization; exact semantics remain OPEN.

## 11. Clinician workflows

Consultation workspaces, consent-aware speech-to-text, deterministic adaptive intake, extraction review, medication safety warnings, alerts, and priority queues are PLANNED. Clinical extraction requires clinician validation. Medication warnings must use deterministic rules or validated sources rather than an LLM alone; the [medication safety check contract](../contracts/api/medication-safety/medication-safety-check.v1.yaml) (HC-160) encodes this by allowing only `deterministic_rule_set` or `validated_source` as the safety source and keeping AI explanations optional and advisory. Its provider is OPEN. AI must not independently diagnose, prescribe, or triage critical cases.

## 12. Research compute-to-data

```text
research code -> Research Portal/Service -> Governance authorization
              -> Hospital Node execution boundary -> controlled result
              -> researcher
```

Compute-to-Data is the preferred CONFIRMED model. Execution, isolation, approved packages, aggregation, disclosure review, and sandbox technology remain OPEN. Unrestricted export of raw hospital databases to researcher machines is not the target architecture.

## 13. Communication contracts

Cross-component communication uses explicit, versionable APIs, events, Federation contracts, schemas, or application ports. Repository-level definitions belong in `contracts/`. Contracts describe communication and must not expose internal tables or create direct SQL coupling.

## 14. Data ownership

- Hospital Nodes control clinical source data and local persistence.
- The Governance Node controls governance decisions and authorization/audit records.
- The Research Portal manages projects subject to Governance authorization.
- Mobile products consume authorized views.
- The company orchestrates its services but does not gain unrestricted clinical ownership.
- The OPTIONAL ledger anchors governance proofs only.

## 15. Runtime and deployment model

Hospital Nodes and the Governance Node are distinct deployable trust boundaries. Hospital Nodes are expected to become containerized, but container choices are OPEN pending ADRs.

The web portals use React + TypeScript + Vite as client-side SPAs with static build output ([ADR-0001](decisions/ADR-0001-web-frontend-technology.md)), styled with Tailwind CSS v4 and the `design-system/` package ([ADR-0002](decisions/ADR-0002-web-design-system.md)).

Patient App and Clinician App will be independent Flutter + Dart projects targeting Android first ([ADR-0004](decisions/ADR-0004-mobile-technology.md)).

Every backend runtime (Hospital Node, Governance Node, Federation, Research, Notifications, AI Services) is a separate Python project using FastAPI as its inbound HTTP adapter, with its own pinned dependencies and no code imports between projects ([ADR-0003](decisions/ADR-0003-backend-runtime-strategy.md)). One Hospital Node codebase runs as one process per hospital, with separate configuration and storage. FastAPI and Pydantic stay in adapters, infrastructure, and the composition root; Domain and Application use the standard library only. A runtime is created only when a ticket needs it.

Persistence, hosting, and topology remain OPEN.

## 16. Development / preview / production

- **Development:** implementation and debugging after stack selection.
- **Preview:** production-like build and integration validation with non-production secrets.
- **Production:** explicitly approved user-facing deployment.

Target validation flow: `Development -> Lint/Tests -> Build -> Preview -> Integration/E2E -> Deployment`. Build success alone is not deployment validation.

## 17. Security principles

Use least privilege, explicit identity, scoped and expiring authorization, auditability, data minimization, secret isolation, and denial by default across trust boundaries. Do not place secrets or real patient data in Git or fixtures. Concrete authentication, cryptography, retention, privacy jurisdiction, and threat controls remain OPEN.

## 18. AI principles

AI is advisory, replaceable through ports, and subject to appropriate human review. Provider SDKs stay outside Domain. Mocked AI is not validated intelligence. Research output does not silently become clinical truth.

## 19. Current implementation status

| Area | Status | Notes |
|---|---|---|
| Repository structure | IMPLEMENTED | Boundary folders and README documentation exist. |
| Documentation and planning | IMPLEMENTED | Product vision, architecture, plans, templates, and guidance exist. |
| Patient App | PLANNED | Stack decided by ADR-0004; no dependencies, generated native project, or application code. |
| Clinician App | PLANNED | Stack decided by ADR-0004; no dependencies, generated native project, or application code. |
| Hospital Portal | PLANNED | No UI code; stack decided by ADR-0001. |
| Governance Portal | PLANNED | No UI code; stack decided by ADR-0001. |
| Research Portal | PLANNED | No UI code or notebook execution; stack decided by ADR-0001. |
| Web design system | IMPLEMENTED | Tokens, components, and showcase at D1 (ADR-0002); no portal consumes it yet. |
| Canonical demo data | MOCKED | Fictional JSON fixtures with integrity checks (ADR-0005); read by the Federation Service's simulated nodes (HC-141). |
| Hospital Node | IMPLEMENTED (skeleton) | FastAPI runtime skeleton (HC-110) with empty layers and no product endpoint; health, configuration, and clinical APIs PLANNED; must provide the HC-140 Federation contract, not yet implemented. |
| Governance Node | PLANNED | Boundary documented; runtime not implemented; stack decided by ADR-0003. |
| DMI Adapter | PLANNED | Hospital-local boundary documented; no adapter. |
| Federation Service | IMPLEMENTED (D2) / MOCKED nodes | Contracts in `contracts/federation/` (HC-140); runtime serves the federated patient query with simulated Hospital Nodes (HC-141) and an in-memory node registry whose Governance approval references are unverified (HC-142); no real node-to-node exchange. |
| Notification Service | PLANNED | No provider or runtime implementation; stack decided by ADR-0003. |
| SciAgents Integration | PLANNED | SciAgents exists externally; repository-side contract defined (HC-170); connector is absent. |
| Immutable Audit Ledger | OPTIONAL / PLANNED | Governance-only concept; no adapter or ledger. |
| AI Services | IMPLEMENTED (skeleton) / MOCKED extraction | FastAPI runtime (HC-150); provider-neutral `AiProvider` port with a deterministic mock adapter (HC-151); clinical extraction contract v1 with a deterministic fixture mock (HC-152); no real AI capability, library, or provider. |
| Authentication and persistence | PLANNED | No implementation or selected technology. |
| IoT | OPTIONAL | PlatformIO placeholder is prepared; hardware/framework/protocol are OPEN. |
| GitHub templates/workflows | IMPLEMENTED | Templates and manual placeholder workflows exist; product CI is not configured. |

See [CURRENT_STATUS.md](CURRENT_STATUS.md) before claiming implementation.

## 20. Open questions

Technology, interoperability, security, and deployment decisions that remain unresolved are maintained in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). Do not answer them without evidence and an accepted ADR where required.
