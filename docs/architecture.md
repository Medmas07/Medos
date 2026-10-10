# Architecture

## Ecosystem overview

HackCure is structured as a federated healthcare ecosystem. Autonomous Hospital Nodes retain clinical source data. A separate Ethics / Governance Instance controls institutional validation, synchronization and research authorization, policy and consent governance, and immutable audit integration. Company-managed applications and services provide portals, node distribution, research tooling, billing/subscriptions, and releases without assuming the governance authority's decision rights.

The structure reserves boundaries; it does not select frameworks, databases, protocols, or deployment products.

## Actors

- Patients consume authorized medical views and manage consent, access grants, delegation, and requests.
- Clinicians include public and private physicians, nurses, and clinics operating within granted access.
- Hospitals own and operate autonomous nodes and control their clinical source data.
- The ethics/governance authority validates institutions and authorizes synchronization and research.
- Researchers submit governed projects and compute-to-data jobs and receive controlled results.
- The company manages product distribution and research-platform operations, but does not approve its own governance requests.

## Trust boundaries

```text
Company infrastructure != Ethics authority
Hospital A            != Hospital B
Researcher            != Hospital data owner
Patient application   != Hospital database
AI system             != Clinical authority
```

Authentication, authorization, minimization, and audit must be designed at every crossed boundary. AI output is advisory where clinical consequences exist and requires appropriate human or clinical validation.

## Company-managed components

Company-managed surfaces may include the hospital onboarding portal, node distribution and release tooling, the researcher platform, and billing/subscriptions. Company operation does not grant governance decision authority or ownership of hospital clinical data.

## Ethics / Governance components

The governance portal and Governance Node form the ethics-authority boundary. Future responsibilities include the hospital registry, institutional validation, policies, synchronization and research authorization, consent governance, audit exploration, and ledger verification. Governance decisions are controlled by the governance instance, not by company services.

## Hospital Nodes

Each Hospital Node is an autonomous, eventually containerized deployable instance. Its future boundary may contain local APIs, identity/RBAC, clinical data, a FHIR or other canonical clinical model, consent, audit, synchronization, events/notifications, local storage, health checks, and DMI adapter integration.

Nodes must not share database tables with central services or other hospitals. No central component may use direct SQL access to a Hospital Node. Specific storage, FHIR server, framework, and container technology remain undecided.

## Patient application

The patient mobile product will consume authorized API views for medical timelines, consultations, medications, lab results, consent, clinician access, family delegation, restriction/erasure requests, notifications, and medication safety information. It never connects directly to a hospital database and does not own raw clinical source data.

## Clinician application

The clinician mobile product will provide an authorized workspace for search, history, consultations, intake, speech-to-text, AI-assisted extraction, laboratory assistance, medication safety, alerts, priority queues, and notifications. Role-specific behavior and the mobile framework remain open decisions.

## Research platform

The research portal is the researcher-facing surface for onboarding, subscriptions, projects, requests, documents, dataset requirements, a future Colab-like workspace, monitoring, SciAgents access, and controlled results. Research services orchestrate approved work; they do not directly access hospital persistence.

## AI services

Python is confirmed for future AI components such as clinical extraction, summarization, document analysis, priority assistance, medication explanation, and LLM orchestration. No library or web framework is selected. AI remains outside clinical authority and must be accessed through explicit ports and contracts.

## Integrations

External systems are isolated behind adapter boundaries in `integrations/` and application-owned ports. Integration representations must not leak into domain models.

### DMI / legacy systems

```text
Legacy DMI / HIS -> hospital-specific adapter -> mapping / normalization -> canonical clinical model
```

There is no assumed universal DMI implementation. Hospital-specific adapters may be introduced only when actual systems and mappings are known.

### SciAgents

SciAgents is an external system to integrate, not reimplement. Its eventual boundary may contain a client, request/response schemas, authentication, timeouts, error mapping, and experiment provenance.

## Communication contracts

Components communicate through explicit contracts, ports, APIs, events, or federation interfaces. A component must not directly depend on another component's internal persistence model. Significant cross-component contracts belong under `contracts/` and must be versionable.

Allowed:

```text
Patient App -> Patient API contract -> Federation service
Hospital Node -> Sync contract -> Governance Node
```

Forbidden:

```text
Research service -> direct SQL access -> Hospital database
Patient app -> direct database connection
```

Within every business backend, dependencies point inward:

```text
infrastructure / framework -> adapters -> application -> domain
```

The Domain knows no framework, database, ORM, broker, external API, Docker, cloud provider, or infrastructure library. Application-defined ports isolate external details; adapters implement those ports. Do not scaffold layers or speculative interfaces until a use case needs them.

## Federation

Federation supports node identity and discovery, explicit data scope, temporary authorization, synchronization requests, signatures, expiration, result envelopes, and error handling. `contracts/federation/` is the canonical location for these definitions when validated. Federation coordinates autonomous nodes and must not become a centralized clinical database.

## Compute-to-data

```text
Research Portal -> Research Service -> Research Job Contract
                -> Governance authorization -> Hospital Node execution boundary
                -> Controlled result -> Research Service
```

The intended direction sends approved code or jobs to authorized execution environments rather than downloading raw clinical data. Execution, isolation, review, and result-disclosure mechanisms remain open decisions.

## Blockchain / immutable audit boundary

```text
Governance Application -> AuditLedgerPort <- BlockchainAdapter -> Permissioned Ledger
```

Blockchain is an outbound adapter detail and never the clinical database. A future ledger may hold only minimized proofs such as event or authorization IDs, resource hashes, timestamps, versions, signatures, and organization identifiers—never raw medical data.

## Data ownership

- Clinical source data is owned or controlled by Hospital Nodes.
- Governance decisions are owned or controlled by the governance instance.
- Research projects are managed by the company research platform subject to governance authorization.
- Audit proofs may be anchored in a governance ledger.
- Mobile applications consume authorized views and do not gain raw-data ownership.

## Consent and authorization

Consent and authorization cross trust boundaries and require explicit, auditable contracts. Consent does not replace legal authority, purpose limitation, or access control. Detailed policy semantics, identity model, jurisdiction, retention, and revocation behavior remain open.

## Runtime environments

- Development supports implementation and debugging after a stack is selected.
- Preview validates production builds and production-like boundaries with non-production secrets.
- Production is the user-facing environment and requires explicit deployment decisions and validation.

IoT remains optional. Hardware, firmware framework, and device/backend protocol are undecided.

## Deployment strategy

```text
Development -> Lint / Tests -> Build -> Local Production Preview
            -> Integration / E2E Validation -> Deployment
```

Hospital and Governance Nodes are separate deployable trust boundaries. Concrete packaging, topology, hosting, databases, and Docker adoption require accepted decisions. See [deployment documentation](deployment/README.md).

## Testing strategy

Within components, prioritize Domain tests and Application/use-case tests before adapter integration. `tests/integration/` and `tests/e2e/` are reserved for future contract, cross-service integration, federation, deployment, and end-to-end journey tests. No technology-specific test framework is selected.

## Open questions

- Which workflows and acceptance criteria are validated for the hackathon MVP?
- Which canonical clinical model and interoperability profiles are required?
- Which jurisdictions, privacy obligations, threat model, and consent semantics apply?
- How are organizations, nodes, patients, clinicians, and researchers identified?
- Which synchronization and compute-to-data protocols meet the authorization model?
- Which runtime stacks, persistence technologies, ledger, and deployment topology are justified?
