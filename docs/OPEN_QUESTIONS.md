# Open Questions

These questions are OPEN. Do not answer them through implementation without the required evidence and ADR.

- How will the Flutter mobile apps reuse or translate the web design-system tokens without depending on the React package ([ADR-0002](decisions/ADR-0002-web-design-system.md), [ADR-0004](decisions/ADR-0004-mobile-technology.md))?
- How will one Hospital Node codebase load per-hospital configuration (identity, port, storage) for several demo hospitals? (The runtime itself is decided by [ADR-0003](decisions/ADR-0003-backend-runtime-strategy.md).)
- What canonical clinical model, FHIR version, profiles, terminology, and validation strategy are required?
- Which persistence technologies and data models fit each bounded context?
- Which authentication provider and identity architecture will serve patients, clinicians, researchers, organizations, and Nodes?
- How will consent, legal authority, revocation, retention, restriction, and erasure differ by jurisdiction?
- Which transport and protocol will carry Federation queries, synchronization, and node discovery?
- How will node identity, signing, authorization tokens, key rotation, and trust establishment work?
- Is an Immutable Audit Ledger required, and if so which permissioned ledger technology is justified?
- Which AI providers, models, hosting mode, evaluation criteria, and clinical review controls are acceptable?
- Which components may call the AI clinical extraction API with clinical source text, and is AI Services hosted inside the hospital boundary or as a company service? This decides whether clinical text leaves the Hospital Node. ([HC-152 contract](../contracts/api/ai/clinical-extraction.v1.yaml).)
- Should extracted measurement units be coded in UCUM and items mapped to a terminology (for example SNOMED CT) before clinician review, or only after?
- Which validated medication-interaction and clinical terminology sources will be used?
- Which component provides the medication safety check ([HC-160 contract](../contracts/api/medication-safety/medication-safety-check.v1.yaml))? Candidates include the Hospital Node serving the clinician or a dedicated service; a dedicated service needs an ADR. The contract is stateless, so the caller assembles the authorized medication history either way.
- Which medication terminology (for example RxNorm or ATC) identifies medications across organizations, so interactions can be matched reliably?
- Which research execution sandbox, package policy, isolation controls, and output-disclosure process are required?
- Which notification providers and delivery protocols will be used?
- Which container runtime, deployment providers, hosting topology, observability stack, and disaster-recovery approach are appropriate?
- Which actual DMI/HIS systems, interfaces, schemas, mappings, and local installation constraints apply to each participating hospital?
- Is IoT required; if so, which hardware, embedded framework, protocol, and security constraints apply?
- Which business-model assumptions from the product vision are validated for the hackathon and for later operation?
