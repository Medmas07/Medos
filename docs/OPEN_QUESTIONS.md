# Open Questions

These questions are OPEN. Do not answer them through implementation without the required evidence and ADR.

- Where will the HC-004 web design system live so all three portals can reuse it without a generic `shared/` folder or a non-product entry under `apps/`? (The web framework itself is decided by [ADR-0001](decisions/ADR-0001-web-frontend-technology.md).)
- How will one Hospital Node codebase load per-hospital configuration (identity, port, storage) for several demo hospitals? (The runtime itself is decided by [ADR-0003](decisions/ADR-0003-backend-runtime-strategy.md).)
- What canonical clinical model, FHIR version, profiles, terminology, and validation strategy are required?
- Which persistence technologies and data models fit each bounded context?
- Which authentication provider and identity architecture will serve patients, clinicians, researchers, organizations, and Nodes?
- How will consent, legal authority, revocation, retention, restriction, and erasure differ by jurisdiction?
- Which transport and protocol will carry Federation queries, synchronization, and node discovery?
- How will node identity, signing, authorization tokens, key rotation, and trust establishment work?
- Is an Immutable Audit Ledger required, and if so which permissioned ledger technology is justified?
- Which AI providers, models, hosting mode, evaluation criteria, and clinical review controls are acceptable?
- Which validated medication-interaction and clinical terminology sources will be used?
- Which research execution sandbox, package policy, isolation controls, and output-disclosure process are required?
- Which notification providers and delivery protocols will be used?
- Which container runtime, deployment providers, hosting topology, observability stack, and disaster-recovery approach are appropriate?
- Which actual DMI/HIS systems, interfaces, schemas, mappings, and local installation constraints apply to each participating hospital?
- Is IoT required; if so, which hardware, embedded framework, protocol, and security constraints apply?
- Which business-model assumptions from the product vision are validated for the hackathon and for later operation?
