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

CONFIRMED autonomous hospital-controlled boundary for local clinical integration, storage, consent enforcement, audit generation, DMI Adapter ownership, federation interfaces, and local Compute-to-Data execution. Its runtime skeleton is IMPLEMENTED with a MOCKED, read-only clinical repository loaded from fictional demo data (HC-113). It serves its Federation, patient-history (HC-114), audit (HC-116), and access-grant (HC-115) interfaces. HC-183 implements the Hospital-side research execution contract at D3 for one bounded installed aggregate: authorization scope and expiry are checked locally before access, and only empty, suppressed, or aggregate results leave the node. HC-186 runs that installed aggregate in a restricted child process with an empty environment, isolated Python/site-package mode, a temporary working directory, denied post-startup filesystem/network/import/process audit events, payload/output quotas, a parent wall-time limit, and POSIX `rlimit` where available. On Windows, OS resource limits are explicitly `parent_enforced`; this is defense in depth for installed code, not container-grade production isolation. Submitted artifacts and arbitrary code are not executed. Clinical source data, including internal research subjects, stays inside the node. Durable state, authenticated callers and Governance artifacts, persistence, and a real DMI connection remain PLANNED (the HC-121 adapter is MOCKED, the HC-123 Hospital B adapter reads a simulated export, and neither is wired in).

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

Python is CONFIRMED. Clinical extraction is IMPLEMENTED with Claude (Claude Agent SDK) as primary provider and a local Ollama model as fallback behind the provider-neutral `AiProvider` port ([ADR-0006](decisions/ADR-0006-ai-provider-strategy.md)); it is not clinically validated. The LLM-assisted review of hospital onboarding dossiers is IMPLEMENTED (HC-154) through the same port: advisory findings that must cite the dossier, never an approval or rejection. Lab result extraction is IMPLEMENTED (HC-155) through the same port: the model only reads the report, every value is verified against its quote, and abnormal flags are computed deterministically from the printed reference range, never by the model. Medication warning explanation is IMPLEMENTED (HC-156): it only words a deterministic warning, and model text that fails deterministic checks (both medications named, the warning's severity kept, no dose, no recommendation) is replaced by a template. Priority queue explanation is IMPLEMENTED (HC-157) the same way: it only words an entry that a deterministic priority method ranked, never ranks or triages, and model text that fails deterministic checks (every factor cited, the entry's priority kept, no invented number, no urgency, interpretation, or directive) is replaced by a template. Summarization and research assistance are PLANNED.

### Federation

PLANNED coordination for node discovery, authorization, cross-node queries, synchronization, aggregation, failures, and audit. It must not become a central clinical database.

### Notifications

PLANNED delivery of authorized patient, clinician, researcher, hospital, and governance notifications. Providers and protocols are OPEN.

### SciAgents Integration

SciAgents is an existing external system and is not implemented here. The repository-side [investigation contract](../contracts/api/sciagents/scientific-investigation.v1.yaml) (HC-170) accepts a display question, exactly two non-identifying biomedical concepts, and opaque workflow references, never clinical-result content, and marks results as not for clinical decisions. The D2 HC-171 client adapter maps only the concept pair to the external HTTP API, normalizes polling states, errors, empty findings, and provenance, and keeps workflow metadata inside Hackcure. HC-172 exposes that provider-neutral contract from the integration runtime to the Research Portal; the browser never receives the upstream SciAgents URL. HC-173 renders the existing polling state, adapter-owned stage, optional estimated percentage, and update time without inventing unavailable progress. Correlation is process-local; authentication, shared persistence, retries, and SSE consumption remain PLANNED.

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

The Hospital Node owns the DMI port, `DmiSource` in its `application/` layer (DEFINED at D1, HC-120): it returns one patient's records in the Node's canonical model, plus the source entries left unmapped, by reference and reason code, so nothing is dropped silently. The port is internal to each Node and is not a cross-component contract. The DMI Adapters that implement it live at `instances/hospital-node/adapters/dmi/`: a MOCKED local adapter over a simulated, fictional DMI exists (D2, HC-121) but is not wired into the Node runtime. The mapping strategy (D2, HC-122) is DEFINED and IMPLEMENTED as adapter-side building blocks: each hospital translates its local codes through its own explicit, versioned mapping tables, inside its adapter, and an entry that cannot map completely is rejected whole with a shared `RejectionReason`; the canonical model is the Node's own, and FHIR remains OPEN. A sample hospital-specific adapter (D3, HC-123) is IMPLEMENTED for Hospital B against a simulated DMI: it reads that DMI's fictional nightly export in its own format and maps it with Hospital B's tables, held in Hospital B's local adapter configuration; it is not wired into the Node runtime. Only the corresponding Hospital Node owns their implementation, mappings, and configuration. A central service connecting directly to every hospital DMI is forbidden.

## 8. Governance and authorization

The company may operate product surfaces but is not the Governance / Ethics Authority. Hospital approval, synchronization authorization, research authorization, and governance policies belong to the Governance Node. Authorization should eventually encode identity, purpose, scope, duration, policy, and consent/legal authority, with auditable decisions.

## 9. Blockchain / immutable ledger boundary

```text
Governance Application -> AuditLedgerPort <- Blockchain Adapter
                                           -> Permissioned Immutable Audit Ledger
```

Ledger integration is OPTIONAL and belongs inside Governance. The port's default adapter is a simulated immutable ledger in the Governance Node's memory (HC-191, MOCKED), not a blockchain; each proof holds its payload's SHA-256 hash, verified by the Node against its audit trail (HC-192). [ADR-0007](decisions/ADR-0007-permissioned-audit-ledger.md) selects Hyperledger Besu (QBFT), with validators intended to be co-operated by independent organizations. Its opt-in adapter (HC-194, D4) anchors each decision's minimized canonical payload in an append-only contract that only the Governance Node's account may write and that computes the hash itself. It is not VALIDATED against a running Besu node, and with a single local validator it gives no assurance independent of the Governance Node. A ledger may anchor minimized IDs, hashes, timestamps, versions, signatures, and organization identifiers. Patient records, diagnoses, prescriptions, lab results, consultation notes, images, and raw FHIR resources are forbidden on-chain. Blockchain is never the clinical database.

## 10. Patient access and consent

Each Hospital Node lists, records, and revokes a patient's access grants through [`patient-access-grants.v1.yaml`](../contracts/api/patient-access/patient-access-grants.v1.yaml) and enforces them itself (HC-115, IMPLEMENTED at D2 over a MOCKED in-memory store, callers not authenticated). A grant recorded on one node does not reach the others; propagation is OPEN. The Governance Node evaluates a synchronization relying on a patient grant against the target organization's node, over that same API, when reviewing and before each exchange, and keeps no copy: a revocation there stops the authorization (HC-136, IMPLEMENTED at D3; node discovery and service authentication OPEN). Delegation, restriction/erasure requests, and the Patient App experiences are PLANNED. Authorized views do not transfer source-data ownership. Consent is not a substitute for legal authority, policy, identity, or technical authorization; exact semantics remain OPEN.

## 11. Clinician workflows

Consultation workspaces, consent-aware speech-to-text, deterministic adaptive intake, extraction review, medication safety warnings, alerts, and priority queues are PLANNED. Clinical extraction requires clinician validation. Medication warnings must use deterministic rules or validated sources rather than an LLM alone; the [medication safety check contract](../contracts/api/medication-safety/medication-safety-check.v1.yaml) (HC-160) encodes this by allowing only `deterministic_rule_set` or `validated_source` as the safety source and keeping AI explanations optional and advisory. Each Hospital Node serves it ([ADR-0008](decisions/ADR-0008-medication-safety-check-host.md)): the deterministic engine is IMPLEMENTED (HC-162, D2) over MOCKED fictional rules by default. A node can be configured to use the validated ONC high-priority list instead (HC-163, D3, [ADR-0009](decisions/ADR-0009-validated-interaction-source.md)): a minimum, non-exhaustive set of contraindicated pairs. No product calls it yet. AI must not independently diagnose, prescribe, or triage critical cases.

## 12. Research compute-to-data

```text
research code -> Research Portal/Service -> Governance authorization
              -> Hospital Node execution boundary -> controlled result
              -> researcher
```

Compute-to-Data is the preferred CONFIRMED model. HC-183 implements one bounded local aggregate, HC-184 implements its controlled cross-node aggregation without reconstructing suppressed cells, HC-185 adds a fail-closed Research Service validation gate, and HC-186 adds restricted process isolation for the installed aggregate. General-purpose submitted-code execution, container-grade isolation, approved-package distribution, production disclosure review, and production sandbox technology remain OPEN. Unrestricted export of raw hospital databases to researcher machines is not the target architecture.

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
| Patient App | IMPLEMENTED (D1 shell) | Flutter Android shell, fictional local identity, navigation, and explicit UI states; feature data/contracts remain PLANNED. |
| Clinician App | PLANNED | Stack decided by ADR-0004; no dependencies, generated native project, or application code. |
| Hospital Portal | IMPLEMENTED (shell, D1) | HC-050 shell with MOCKED fixture-backed onboarding dashboard; registration flow (HC-051), organization profile (HC-052), document upload (HC-053), agreements workflow (HC-054), technical questionnaire (HC-055), DMI / HIS questionnaire (HC-056), automated review with simulated assisted review (HC-057), human validation state (HC-058), approval page displaying Governance decisions (HC-059), Node configuration summary (HC-060), demo Node package download (HC-061), installation guide (HC-062), and Node status dashboard (HC-063) with MOCKED submission, generation, or status; onboarding and health-status contracts PLANNED. |
| Governance Portal | PLANNED | No UI code; stack decided by ADR-0001. |
| Research Portal | IMPLEMENTED (product flows D1, SciAgents connection/progress D2) | HC-090 to HC-102 provide the fixture-backed portal workflows and visibly MOCKED Compute-to-Data/SciAgents demonstrations. HC-172 adds configurable submission and polling through the provider-neutral SciAgents Integration API, and HC-173 displays its explicit execution state, stage, optional percentage, and update time; the browser never calls the upstream provider and no fixture is used as a live fallback. Real notebook execution and consumption of the HC-182 Research Service contract remain PLANNED. |
| Web design system | IMPLEMENTED | Tokens, components, and showcase at D1 (ADR-0002); consumed by the Hospital Portal, Governance Portal, and Research Portal shells. |
| Canonical demo data | MOCKED | Fictional JSON fixtures with integrity checks (ADR-0005); read by the Federation Service's simulated nodes (HC-141). |
| Hospital Node | IMPLEMENTED (D2/D3/D4) / MOCKED source data | FastAPI runtime with liveness, per-hospital configuration, patient-history/Federation, audit, and access-grant APIs (HC-110 to HC-116). HC-183 implements bounded local research execution with authorization-envelope checks and controlled aggregate/empty/suppressed outcomes. HC-186 isolates the installed aggregate in a restricted child process and reports the enforced controls; it is not container-grade production isolation. HC-162 serves the medication safety check with a deterministic engine over MOCKED fictional rules (ADR-0008), or over the validated ONC high-priority list when configured (HC-163, ADR-0009). The canonical local repository is MOCKED; arbitrary submitted code, authenticated authorization, persistence, and DMI integration are PLANNED. |
| Governance Node | Partially IMPLEMENTED (D2/D3) | FastAPI runtime with `GET /health` (HC-130), the hospital approval API (HC-131), the synchronization request API and the provider side of the Federation's synchronization authorization check (HC-132), the research access request API and the provider side of the Research Service's authorization check (HC-133), the governance audit API recording its own requests, decisions, and checks (HC-134), and the D3 governance policy engine applying a versioned, effective-dated policy to every review and decision, each decision citing its version (HC-135), and D3 consent policy evaluation against the grants of the Hospital Node holding them, over real HTTP (HC-136), over in-memory storage seeded from fictional data; callers not authenticated; patient grants checked against fictional grants (MOCKED). Each recorded decision is anchored in a simulated immutable ledger (HC-191, MOCKED); a real ledger is OPTIONAL / PLANNED. |
| DMI Adapter | Port DEFINED (D1); mock adapter MOCKED (D2); mapping strategy IMPLEMENTED (D2); sample hospital-specific adapter IMPLEMENTED against a simulated DMI (D3) | Node-owned `DmiSource` port and conformance check (HC-120); MOCKED local adapter over fictional demo data (HC-121); mapping building blocks (HC-122); Hospital B adapter over a fictional legacy export (HC-123); nothing calls the port at runtime, and no real DMI is connected. |
| Federation Service | IMPLEMENTED (D2/D3) | Contracts in `contracts/federation/` (HC-140). Federated patient query over real HTTP to registered nodes by default (HC-145), with HC-141's MOCKED simulated nodes as an explicit opt-in. In-memory node registry with unverified Governance approval references (HC-142). Real HTTP capability discovery (HC-143), used to route queries around nodes that cannot answer (HC-146). Retries and an in-memory circuit breaker for node calls (HC-147). Governance checks of synchronization decisions (HC-144). The Hospital Node serves its node interface and the Governance Node the synchronization authorization check (HC-132). |
| Research Service | IMPLEMENTED (D3/D4), integration not VALIDATED | HC-182 orchestrates Governance authorization and HC-180 Hospital Node executions through application-owned ports and real HTTP adapters. HC-184 aggregates the bounded HC-183 participant-count/HbA1c results. HC-185 validates exact result and metadata shape, disclosure threshold, provenance binding, timestamp order, bounded columns, cells, and HC-186 sandbox evidence before release; rejected output is removed. Empty, suppressed, partial, unavailable, and rejected states remain explicit. It never reconstructs suppressed cells or accesses hospital persistence. The Governance Node provides its authorization check (HC-133); a local end-to-end job completes when the decision's scope fits the HC-183 aggregate. No arbitrary submitted-code execution, general-purpose aggregation, container-grade sandbox, durable persistence, authentication, or production disclosure integration. |
| Notification Service | PLANNED | No provider or runtime implementation; stack decided by ADR-0003. |
| SciAgents Integration | IMPLEMENTED (contract D1, adapter, Portal connection and progress D2), live integration not VALIDATED | SciAgents exists externally. HC-170 v1.1 defines the two-concept research-only contract; HC-171 implements the server-side adapter, HC-172 exposes it to the Research Portal, and HC-173 displays the contract's polling progress without inferring a missing percentage. Fixtures remain visibly MOCKED; no fallback impersonates live integration. Tests use HTTP test doubles; no live endpoint, authentication, durable state, retry policy, or SSE consumer is validated. |
| Immutable Audit Ledger | OPTIONAL; port IMPLEMENTED (D1), simulated ledger IMPLEMENTED (D2, MOCKED), payload hashing IMPLEMENTED (D2), Besu adapter IMPLEMENTED (D4, opt-in), not VALIDATED | The Governance Node's application-owned `AuditLedgerPort` and its use cases exist (HC-190): only a recorded decision's minimized payload (event, decision, outcome, time, organizations, version) can be anchored. Its only adapter is a simulated immutable ledger inside the Governance Node (HC-191): append-only, in memory, not a blockchain, anchoring each decision as it is recorded and served read-only by `governance-ledger-proofs.v1.yaml`. Each proof holds its payload's SHA-256 hash, served with the Node's verification (HC-192); not a signature. HC-194 adds an opt-in Hyperledger Besu (QBFT) adapter ([ADR-0007](decisions/ADR-0007-permissioned-audit-ledger.md)), tested in an in-process EVM but not against a running Besu node; one local validator, so no independent assurance. |
| AI Services | IMPLEMENTED (extraction, hospital document review, lab extraction, medication warning and priority queue explanations) | FastAPI runtime (HC-150); `AiProvider` port (HC-151) with Claude, Ollama, and mock adapters plus a fallback chain (ADR-0006); clinical extraction contract v1 (HC-152) served by real providers (HC-153) or a fixture mode (MOCKED); not clinically validated. Hospital document review contract v1 (HC-154): advisory, cited findings on onboarding dossiers from the same providers, or deterministic rules (MOCKED, opt-in); not validated, and no consumer calls it yet. Lab extraction contract v1 (HC-155): structured lab results verified against the report, with flags computed from the printed range, never by the model; fixture mode MOCKED; not clinically validated. Medication warning explanation contract v1 (HC-156): the medication contract's `Explanation`, from checked model text or a deterministic template; Hospital Nodes attach it to their warnings when configured to (HC-164). Priority queue explanation contract v1 (HC-157): words a deterministically ranked queue entry, from checked model text or a template; never ranks or triages; no Priority Engine or consumer yet. |
| Authentication and persistence | PLANNED | No implementation or selected technology. |
| IoT | OPTIONAL | PlatformIO placeholder is prepared; hardware/framework/protocol are OPEN. |
| GitHub templates/workflows | IMPLEMENTED | Templates and manual placeholder workflows exist; product CI is not configured. |

See [CURRENT_STATUS.md](CURRENT_STATUS.md) before claiming implementation.

## 20. Open questions

Technology, interoperability, security, and deployment decisions that remain unresolved are maintained in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). Do not answer them without evidence and an accepted ADR where required.
