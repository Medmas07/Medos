# Glossary

- **Hospital Node:** autonomous hospital-controlled runtime boundary for local clinical integration, storage, consent enforcement, audit generation, and Federation participation.
- **Governance Node:** runtime boundary operated conceptually by the Governance / Ethics Authority for institutional, synchronization, and research authorization and governance audit.
- **DMI:** *Dossier Médical Informatisé*; a hospital's existing electronic medical-record system or data environment integrated locally through its Hospital Node.
- **HIS:** Hospital Information System; a broader hospital operational/clinical system that may be a DMI Adapter source.
- **FHIR:** Fast Healthcare Interoperability Resources; a possible interoperability representation whose exact version and profiles remain OPEN.
- **Federation:** controlled discovery, authorization, query, synchronization, and result coordination across autonomous Nodes without one unrestricted central clinical database.
- **Compute-to-Data:** model in which authorized code executes near controlled data and only controlled results return to the researcher.
- **SciAgents:** an existing external scientific-agent system integrated through contracts and an adapter; it is not implemented here.
- **Consent:** a recorded patient permission or preference; it does not by itself replace legal authority, policy, identity, or authorization.
- **Authorization:** an explicit decision granting a defined actor a scoped, purpose-bound, and possibly time-limited action.
- **Audit:** an attributable record of relevant requests, decisions, access, or actions.
- **Immutable Audit Ledger:** OPTIONAL governance-controlled mechanism for anchoring minimized integrity proofs; never a clinical database.
- **Clinical Source Data:** original clinical records controlled by the hospital and its Hospital Node.
- **Canonical Clinical Model:** normalized clinical representation inside a Hospital Node; its exact FHIR/internal strategy remains OPEN.
- **Mocked Behavior:** demo-only behavior or fictional fixtures that do not constitute a production capability.
- **Validated Behavior:** implemented behavior verified by relevant automated tests or applicable live/runtime validation.
