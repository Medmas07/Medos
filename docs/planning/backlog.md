# Implementation Backlog

Temporary `HC-*` identifiers are planning IDs, not remote GitHub issues. Work is demo-first: visible product value and deterministic mocks precede backend depth. Mocks must be identifiable internally and must not be presented as production-ready. No ticket authorizes real health data.

Each row uses: **ID — [Type] Title** · Priority · Effort · MVP, followed by its intended outcome.

## Epic A — Product foundation

- **HC-001 — [Architecture] Select frontend technology** · P0 · XS · MVP Yes. Evaluate and select one web technology for all three portals; record an ADR and development/build commands. Do not implement portals here.
- **HC-002 — [Architecture] Select mobile technology** · P0 · XS · MVP Yes. Evaluate options for both mobile apps; record an ADR, establish the Android path, and define the shared platform strategy.
- **HC-003 — [Architecture] Select backend/runtime strategy** · P0 · S · MVP Yes. Decide runtimes for both Nodes and core company services; Python remains confirmed for AI while NestJS, FastAPI, and alternatives remain open until this decision.
- **HC-004 — [UI] Establish visual design system** · P0 · M · MVP Yes. Define reusable typography, spacing, buttons, fields, cards, badges, tables, alerts, navigation, timeline visuals, and status colors.
- **HC-005 — [Data] Create coherent demo dataset** · P0 · M · MVP Yes. Create fictional, reusable data for three hospitals, clinicians, at least three patients, consultations, medications, labs, access grants, research/sync requests, and alerts. Never use real health data.

## Epic B — Patient experience

- **HC-010 — [UI] Patient app shell and navigation** · P0 · S · MVP Yes. Provide the visible Patient App structure.
- **HC-011 — [UI] Patient home dashboard** · P0 · S · MVP Yes. Show health summary, recent events, notifications, active grants, and quick actions using mock data where needed.
- **HC-012 — [UI] Federated patient timeline** · P0 · M · MVP Yes. Visually combine history from Hospital A, a private doctor, and Hospital B; mock federation is acceptable.
- **HC-013 — [UI] Patient medical event details** · P0 · S · MVP Yes. Show organization, clinician, date, type, medication, and applicable lab information for a timeline event.
- **HC-014 — [UI] Patient medications view** · P0 · S · MVP Yes. Show active and historical medications from multiple providers.
- **HC-015 — [UI] Grant doctor access** · P0 · M · MVP Yes. Let a patient select a physician, scope, and duration; mock/local state is acceptable initially.
- **HC-016 — [UI] Delegate access to trusted relative** · P1 · M · MVP Yes. Support scoped family or caregiver access.
- **HC-017 — [UI] Revoke access** · P1 · S · MVP Yes. Make doctor/family access revocation visible.
- **HC-018 — [UI] Digital erasure/restriction request** · P1 · S · MVP Yes. Provide a request form and status without promising automatic deletion.
- **HC-019 — [UI] Patient notifications center** · P1 · S · MVP Yes. Present initially mocked notifications.

## Epic C — Clinician experience

- **HC-030 — [UI] Clinician app shell and navigation** · P0 · S · MVP Yes. Provide the visible Clinician App structure.
- **HC-031 — [UI] Clinician dashboard** · P0 · S · MVP Yes. Show queue, alerts, appointments/events, and urgent items.
- **HC-032 — [UI] Intelligent patient queue** · P0 · M · MVP Yes. Show deterministic mocked priority and its explanation.
- **HC-033 — [UI] Authorized patient list** · P0 · S · MVP Yes. Show patients the clinician is currently authorized to access.
- **HC-034 — [UI] Clinician patient longitudinal history** · P0 · M · MVP Yes. Reuse the coherent federated patient demo data.
- **HC-035 — [UI] Consultation workspace** · P0 · M · MVP Yes. Include notes, patient context, consent state, and actions.
- **HC-036 — [UI] Speech-to-text consultation experience** · P0 · M · MVP Yes. Demonstrate record → transcript → extraction; mocked transcription is acceptable.
- **HC-037 — [UI] Adaptive intake experience** · P0 · M · MVP Yes. Implement deterministic branching across complaint, location, severity, duration, and associated symptoms.
- **HC-038 — [AI/UI] Clinical extraction review** · P0 · M · MVP Yes. Display fixture-derived symptoms, values, medications, observations, and missing information for clinician accept/edit/reject.
- **HC-039 — [UI] Laboratory result extraction view** · P1 · S · MVP Yes. Show extracted and potentially abnormal values; mock extraction is acceptable.
- **HC-040 — [UI] Medication interaction warning** · P0 · M · MVP Yes. Demonstrate a cross-provider conflict, involved medications, provenance, explanation, and clinician validation using deterministic fixtures.

## Epic D — Hospital onboarding

- **HC-050 — [UI] Hospital portal shell** · P0 · S · MVP Yes. Provide the visible Hospital Portal structure.
- **HC-051 — [UI] Hospital registration workflow** · P0 · M · MVP Yes. Present the onboarding workflow from account details through submission.
- **HC-052 — [UI] Hospital document upload** · P0 · S · MVP Yes. Demonstrate document submission; mock processing is acceptable.
- **HC-053 — [UI] Agreements and declarations** · P0 · S · MVP Yes. Present required agreements and declarations.
- **HC-054 — [UI] Technical questionnaire** · P0 · M · MVP Yes. Capture operating environment, DMI/HIS, databases, network, and contacts conceptually.
- **HC-055 — [UI] Automated review status** · P0 · S · MVP Yes. Simulate completeness, LLM-assisted, and human-review states.
- **HC-056 — [UI] Hospital approval state** · P0 · XS · MVP Yes. Display the hospital's governance approval state.
- **HC-057 — [UI] Hospital Node configuration summary** · P0 · S · MVP Yes. Show the configuration produced for an approved hospital.
- **HC-058 — [UI] Hospital Node download/install page** · P0 · M · MVP Yes. Simulate download and show configuration, platform, version, and installation guidance.
- **HC-059 — [UI] Hospital Node status dashboard** · P1 · M · MVP Yes. Mock online state, health, last synchronization, DMI state, and version.

## Epic E — Governance and ethics

- **HC-070 — [UI] Governance portal shell** · P0 · S · MVP Yes. Provide the ethics-authority portal structure.
- **HC-071 — [UI] Governance dashboard** · P0 · M · MVP Yes. Show pending hospital approvals, synchronization/research requests, alerts, and audit events.
- **HC-072 — [UI] Hospital approval review** · P0 · M · MVP Yes. Inspect submitted hospital information and visually approve/reject; mock backend is acceptable.
- **HC-073 — [UI] Synchronization request review** · P0 · M · MVP Yes. Show requester, target, purpose, scope, duration, consent, and visual approval/rejection.
- **HC-074 — [UI] Research access request review** · P0 · M · MVP Yes. Display the research dossier and requested data scope for decision.
- **HC-075 — [UI] Governance audit timeline** · P1 · M · MVP Yes. Visualize governance decisions and audit events chronologically.
- **HC-076 — [UI] Blockchain proof explorer** · P1 · M · MVP Yes. Show simulated event proofs, hashes, timestamps, organizations, and verification state without claiming real persistence.

## Epic F — Research experience

- **HC-090 — [UI] Research portal shell** · P0 · S · MVP Yes. Provide the visible Research Portal structure.
- **HC-091 — [UI] Researcher dashboard** · P0 · S · MVP Yes. Summarize projects, requests, jobs, and status.
- **HC-092 — [UI] Create research project** · P0 · M · MVP Yes. Provide the project creation flow.
- **HC-093 — [UI] Research protocol/document upload** · P1 · S · MVP Yes. Demonstrate research document submission.
- **HC-094 — [UI] Define requested cohort/data** · P0 · M · MVP Yes. Capture population, variables, participating hospitals, and purpose.
- **HC-095 — [UI] Submit ethics/data access request** · P0 · S · MVP Yes. Submit the research request to governance.
- **HC-096 — [UI] Research request status** · P0 · S · MVP Yes. Display governance decision progress.
- **HC-097 — [UI] Colab-like research workspace** · P0 · L · MVP Yes. Build the interface for notebook cells, run control, status, results, and authorization context; remote execution may be mocked.
- **HC-098 — [UI] Compute-to-data execution visualization** · P0 · M · MVP Yes. Mock job submission, authorization, Hospital A/B execution, aggregation, and result return.
- **HC-099 — [Integration/UI] SciAgents panel** · P0 · M · MVP Yes. Show investigation requests, evidence, hypotheses, contradictions, and citations using static fixtures until integration exists.

## Epic G — Basic backend boundaries

- **HC-110 — [Architecture] Define API conventions** · P1 · S · MVP Yes. Define versioned API, error, and authentication conventions under `contracts/api/`.
- **HC-111 — [Architecture] Define event conventions** · P1 · S · MVP No. Define event naming, envelopes, compatibility, and ownership under `contracts/events/`.
- **HC-112 — [Architecture] Define federation contract conventions** · P1 · M · MVP No. Define versioning and communication conventions under `contracts/federation/`.
- **HC-113 — [Backend] Hospital Node skeleton** · P1 · M · MVP Yes. After HC-003, create only the basic runtime, health endpoint, and Clean/Hexagonal structure.
- **HC-114 — [Backend] Governance Node skeleton** · P1 · M · MVP Yes. After HC-003, create the governance runtime boundary and health structure.
- **HC-115 — [Backend] Mock patient API** · P1 · M · MVP Yes. Serve the shared fictional patient dataset through an explicit contract.
- **HC-116 — [Backend] Mock governance request API** · P1 · M · MVP Yes. Serve demo hospital, synchronization, and research request workflows.
- **HC-117 — [Backend] Mock research job API** · P1 · M · MVP Yes. Serve demo research job state and controlled results.

## Epic H — AI

- **HC-130 — [AI] AI service skeleton** · P1 · M · MVP Yes. Create the Python AI service boundary after HC-003 without coupling domain logic to delivery infrastructure.
- **HC-131 — [AI] LLM provider abstraction** · P1 · M · MVP Yes. Keep business behavior independent of any single provider.
- **HC-132 — [AI] Clinical extraction interface** · P1 · M · MVP Yes. Define the clinical extraction port and reviewable result contract.
- **HC-133 — [AI] Real clinical extraction** · P2 · M · MVP No. Implement extraction only after the interface and validation approach exist.
- **HC-134 — [AI] Hospital document review assistant** · P2 · M · MVP No. Add advisory assistance for onboarding documents with human review.
- **HC-135 — [AI] Clinician priority explanation** · P2 · M · MVP No. Explain deterministic priority results without giving AI clinical authority.
- **HC-136 — [AI] Medication warning explanation** · P2 · M · MVP No. Explain warnings grounded in deterministic rules or validated sources; never make the LLM the sole safety source.

## Epic I — SciAgents

- **HC-150 — [Integration] Define SciAgents communication contract** · P1 · S · MVP Yes. Define requests, responses, authentication, errors, timeouts, and provenance.
- **HC-151 — [Integration] SciAgents client adapter** · P1 · M · MVP Yes. Implement the external adapter without reimplementing SciAgents.
- **HC-152 — [Integration] Connect Research UI to SciAgents** · P1 · M · MVP Yes. Replace or complement fixtures through the adapter contract.

## Epic J — Federation

- **HC-170 — [Federation] Mock cross-hospital federation** · P1 · M · MVP Yes. Return multi-node demo history through one explicit API.
- **HC-171 — [Federation] Node registry** · P2 · M · MVP No. Register discoverable autonomous nodes without centralizing clinical data.
- **HC-172 — [Federation] Node identity** · P2 · M · MVP No. Establish verifiable node identity.
- **HC-173 — [Federation] Synchronization authorization** · P2 · L · MVP No. Enforce governance decisions, scope, purpose, and expiry.
- **HC-174 — [Federation] Node-to-node communication** · P2 · L · MVP No. Communicate through versioned federation contracts rather than shared persistence.
- **HC-175 — [Federation] Cross-node patient query** · P2 · L · MVP No. Query authorized views across nodes without building a central clinical database.

## Epic K — DMI

- **HC-190 — [Integration] Define DMI adapter port** · P1 · S · MVP No. Define the Hospital Node-owned port under its local DMI adapter boundary without assuming one legacy system.
- **HC-191 — [Integration] Mock DMI adapter** · P2 · M · MVP No. Provide deterministic, hospital-local mapping fixtures behind the Node-owned port.
- **HC-192 — [Integration] Sample legacy hospital adapter** · P3 · L · MVP No. Build one justified Hospital Node adapter from actual hospital requirements; do not introduce a central DMI service.

## Epic L — Notifications

- **HC-210 — [UI] Notification center** · P1 · S · MVP Yes. Provide a coherent notification experience across relevant demo surfaces.
- **HC-211 — [Backend] Notification event service** · P2 · M · MVP No. Process versioned notification events after provider/runtime decisions.
- **HC-212 — [Integration] Real-time clinician notifications** · P2 · M · MVP No. Deliver time-sensitive clinician updates through an explicit adapter.
- **HC-213 — [Integration] Mobile push notifications** · P3 · L · MVP No. Integrate a selected push provider after the mobile decision.

## Epic M — Governance depth

- **HC-230 — [Backend] Governance policy engine** · P2 · L · MVP No. Evaluate authorization policy inside the governance boundary.
- **HC-231 — [Backend] Consent persistence** · P2 · M · MVP No. Persist consent with history and auditable status.
- **HC-232 — [Security] Temporary authorization tokens** · P2 · L · MVP No. Issue scoped, expiring authorization artifacts.
- **HC-233 — [Audit] Persistent governance audit** · P2 · M · MVP No. Persist governance audit events independently of ledger anchoring.
- **HC-234 — [Blockchain] AuditLedgerPort** · P2 · S · MVP No. Define the governance application outbound port for minimized audit proofs.
- **HC-235 — [Blockchain] Local simulated immutable ledger** · P2 · M · MVP No. Implement a local adapter for testing without claiming real blockchain persistence.
- **HC-236 — [Blockchain] Real permissioned blockchain adapter** · P3 · XL · MVP No. Integrate a selected ledger behind `AuditLedgerPort`; never store raw medical data.

## Epic N — Research compute-to-data

- **HC-250 — [Research] Define research job contract** · P1 · M · MVP Yes. Define authorized inputs, execution status, provenance, and controlled result envelopes.
- **HC-251 — [Research] Mock distributed research execution** · P1 · M · MVP Yes. Demonstrate multi-hospital execution and aggregation deterministically.
- **HC-252 — [Research] Research job orchestrator** · P2 · L · MVP No. Coordinate authorized jobs without taking ownership of hospital data.
- **HC-253 — [Research] Hospital-side execution agent** · P2 · L · MVP No. Execute approved jobs inside the Hospital Node boundary.
- **HC-254 — [Security] Isolated research execution** · P3 · XL · MVP No. Isolate untrusted research workloads with explicit resource and network controls.
- **HC-255 — [Research] Controlled output validation** · P3 · L · MVP No. Review outputs for disclosure risk before release.

## Epic O — Deployment

- **HC-270 — [DevOps] Build Hospital Node container** · P2 · L · MVP No. Package the selected Hospital Node runtime after its skeleton exists.
- **HC-271 — [DevOps] Hospital Node installation package** · P2 · L · MVP No. Package configuration and installation guidance for approved hospitals.
- **HC-272 — [DevOps] Runtime detection / installation assistant** · P3 · L · MVP No. Detect prerequisites and guide operators; never silently install Docker.
- **HC-273 — [DevOps] Hospital Node health checks** · P2 · M · MVP No. Expose operational readiness and dependency health.
- **HC-274 — [DevOps] Governance Node deployment package** · P2 · L · MVP No. Package the separate governance runtime after deployment decisions.

## Epic P — Security

- **HC-290 — [Security] Authentication foundation** · P1 · M · MVP Yes. Establish explicitly simplified demo authentication with a migration path.
- **HC-291 — [Security] Role-based access** · P2 · M · MVP No. Enforce role and boundary-specific permissions.
- **HC-292 — [Security] Hospital organization identity** · P2 · L · MVP No. Establish organization identity and lifecycle.
- **HC-293 — [Security] Signed federation authorization** · P3 · L · MVP No. Sign and verify scoped federation authorization after identity and token conventions exist.

## Summary

| Priority | Tickets |
|---|---:|
| P0 | 44 |
| P1 | 29 |
| P2 | 26 |
| P3 | 7 |
| **Total** | **106** |

70 tickets are marked MVP; 36 are not.
