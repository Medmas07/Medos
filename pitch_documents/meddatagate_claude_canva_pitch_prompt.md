# Prompt Claude + Canva MCP — Technical Pitch Deck 5 min

You are creating a **5-minute technical pitch deck** in Canva for a federated healthcare data and intelligence platform called **MedDataGate**.

Use Canva MCP to create the presentation directly.

The audience is a technical hackathon jury.

The goal is NOT to present a business model.

The goal is to demonstrate:

1. the technical problem in healthcare data flow;
2. how our architecture repairs each break;
3. how the federated architecture works;
4. how data stays under hospital control;
5. how clinicians and patients benefit technically;
6. how governance and blockchain are used;
7. how research works through Compute-to-Data;
8. how SciAgents adds scientific intelligence;
9. what makes the architecture technically strong and different.

The pitch must remain understandable in about **5 minutes**.

Avoid dense slides.

Prefer:
- diagrams;
- flows;
- architecture views;
- icons;
- technical callouts;
- before/after visual comparisons.

---

# 1. Project Name

## MedDataGate

### Positioning

**Federated Healthcare Data & Intelligence Ecosystem**

### Core idea

MedDataGate is not another centralized EHR.

It is a **federated intelligence and governance layer** that connects existing hospital systems while allowing hospitals to retain control of their clinical data.

Core principle:

> **Connect the care. Keep the data local. Move intelligence instead.**

---

# 2. Problem Context

Healthcare data already exists.

The problem is how it is captured, transferred, structured, synchronized and reused.

The current data journey contains several breaks.

## Break 1 — Patient mobility

When a patient changes doctor, hospital or medical service, they often need to bring their own medical file or explain their history again.

This creates:
- fragmented medical history;
- missing previous information;
- duplicated questions;
- continuity-of-care problems.

## Break 2 — Consultation

During a doctor-patient consultation, important information may be lost.

The discussion contains:
- symptoms;
- context;
- treatments;
- previous events;
- measurements;
- physician observations.

But not everything necessarily becomes structured clinical data.

## Break 3 — Manual entry

Medical information is often manually entered into systems under workload pressure.

This creates risks such as:
- incomplete data;
- manual errors;
- missing fields;
- inconsistent values;
- insufficient validation.

## Break 4 — Separate healthcare services

Different services may request the same information again.

Examples:
- emergency;
- laboratory;
- imaging;
- specialists;
- another hospital.

The problem is not only storage.

It is **lack of synchronization and interoperability**.

## Break 5 — Research and Machine Learning

Later, researchers receive datasets containing:
- missing values;
- duplicates;
- inconsistent records;
- aberrant values;
- incomplete clinical context.

This directly affects ML systems.

Core principle:

> **Garbage in, garbage out.**

Bad clinical data produces bad models and unreliable research results.

---

# 3. Our Technical Response

MedDataGate repairs each break progressively.

Use the visual metaphor:

```text
CURRENT SYSTEM

----X------X------X------X------X---->

        becomes

MEDDATAGATE

----🩹------🩹------🩹------🩹------🩹---->
```

Each bandage represents a technical repair.

## Repair 1 — Unified longitudinal history

```text
Hospital A
      \
Hospital B
       \
Private Doctor
        \
         → Authorized Patient Timeline
```

The patient can access an authorized longitudinal view across multiple providers.

The data does NOT need to be copied into one giant central database.

## Repair 2 — Better clinical capture

```text
Patient consent
      ↓
Speech-to-Text
      ↓
Clinical transcript
      ↓
AI extraction
      ↓
Structured draft
      ↓
Clinician validation
```

If the patient refuses recording:

```text
Adaptive Intake
```

is used instead.

## Repair 3 — Structured + validated data

AI can extract:
- symptoms;
- measurements;
- medication mentions;
- lab values;
- observations;
- missing information.

But:

> **AI output is not automatically clinical truth.**

The clinician reviews and validates the extracted information.

Core principle:

> **AI assists. Humans validate.**

## Repair 4 — Federation instead of centralization

Each hospital runs its own **Hospital Node**.

```text
Legacy DMI / HIS
        ↓
Hospital-specific DMI Adapter
        ↓
Hospital Node
        ↓
Canonical / FHIR representation
        ↓
Federation
```

Each hospital keeps control of its own clinical data.

## Repair 5 — Governed research

```text
Researcher algorithm
        ↓
Governance authorization
        ↓
Hospital Nodes
        ↓
Local execution
        ↓
Controlled aggregation
        ↓
Research result
```

Core principle:

> **Code goes to the data. Data does not go to the researcher.**

---

# 4. System Architecture

The architecture contains five major layers.

## Layer 1 — Existing Hospital Systems

Every hospital may already have:
- DMI;
- HIS;
- databases;
- laboratory systems;
- imaging systems;
- existing internal software.

MedDataGate does NOT require replacing them.

## Layer 2 — Hospital Node

Every hospital runs an autonomous Hospital Node.

```text
Hospital Node
│
├── Local Clinical API
├── Identity / RBAC
├── Clinical Data
├── Consent
├── Audit
├── Federation Client
├── Canonical / FHIR Representation
├── Notifications / Events
├── Health Checks
└── DMI Adapter
```

Important architectural rule:

The DMI adapter belongs **inside the Hospital Node**.

Never use one central DMI service connecting directly to all hospitals.

---

# 5. Hospital-specific DMI Adapter

```text
Hospital A
└── Hospital Node A
    └── DMI Adapter A
        └── DMI A

Hospital B
└── Hospital Node B
    └── DMI Adapter B
        └── DMI B
```

Possible adapter responsibilities:
- schema mapping;
- patient mapping;
- medication mapping;
- laboratory mapping;
- normalization;
- terminology conversion;
- FHIR transformation;
- validation.

This allows interoperability without forcing hospitals to replace their existing systems.

---

# 6. Federation Layer

Hospital Nodes communicate through explicit federation contracts.

Responsibilities may include:
- node discovery;
- node capability discovery;
- authorized queries;
- synchronization requests;
- temporary access authorization;
- cross-node orchestration;
- controlled result aggregation;
- failure handling.

Important:

> The Federation Layer is NOT a centralized clinical database.

---

# 7. Governance / Ethics Node

A separate Governance / Ethics Node handles sensitive authorization.

It answers questions such as:

```text
Who is requesting access?
What data is requested?
Why?
For how long?
Which institutions are involved?
Does consent allow it?
```

Responsibilities include:
- hospital approval;
- synchronization authorization;
- research authorization;
- consent governance;
- policy evaluation;
- audit;
- temporary authorization;
- blockchain proof integration.

Important trust boundary:

```text
Company Platform
        ≠
Governance / Ethics Authority
```

---

# 8. Blockchain Role

Blockchain belongs to the Governance boundary.

It is NOT used as a medical database.

```text
Governance Application
        ↓
AuditLedgerPort
        ↑
Blockchain Adapter
        ↓
Permissioned Ledger
```

Store only proof-like information:
- event ID;
- authorization ID;
- organization ID;
- resource hash;
- timestamp;
- version;
- digital signature.

Never store:
- diagnoses;
- prescriptions;
- patient records;
- lab reports;
- medical images;
- consultation notes;
- raw FHIR resources.

Pitch sentence:

> **Blockchain stores proofs, not patients.**

---

# 9. Patient Application

The Patient App provides an authorized view across the ecosystem.

Core capabilities:
- unified longitudinal history;
- hospital history;
- physician history;
- medications;
- lab results;
- consent management;
- doctor access grants;
- revoke access;
- family delegation;
- restriction / erasure requests;
- notifications.

Example:

```text
2024 — Hospital A
2025 — Private Doctor
2026 — Hospital B
```

This is presented as one timeline without requiring one central clinical database.

---

# 10. Clinician Application

The Clinician App provides:
- authorized patient list;
- patient history;
- consultation workspace;
- speech-to-text;
- adaptive intake;
- AI extraction;
- laboratory extraction;
- medication safety;
- alerts;
- patient priority queue.

---

# 11. Medication Safety

```text
Medication A
prescribed previously at Hospital A

        +

Medication B
new prescription from Doctor B

        ↓

Medication Safety Engine

        ↓

Potential interaction detected
```

Preferred architecture:

```text
Structured medication history
        +
Validated interaction rules / sources
        +
Patient context
        ↓
Medication Safety Engine
        ↓
Potential warning
        ↓
LLM explanation
        ↓
Clinician validation
```

Important:

The LLM must NOT be the only medication safety mechanism.

---

# 12. Research Platform

Researchers use a dedicated Research Platform.

Potential capabilities:
- research project creation;
- protocol upload;
- cohort definition;
- requested variables;
- participating hospital selection;
- ethics requests;
- request status;
- notebook interface;
- Compute-to-Data execution;
- results;
- experiment history;
- SciAgents access.

---

# 13. Compute-to-Data

Traditional model:

```text
Hospital database
        ↓
CSV export
        ↓
Researcher laptop
```

Problems:
- uncontrolled copies;
- privacy risks;
- difficult revocation;
- poor auditability;
- data leaving hospital control.

Our model:

```text
Researcher
    ↓
Research Job
    ↓
Governance Approval
    ↓
Hospital Node A
Hospital Node B
Hospital Node C
    ↓
Local execution
    ↓
Controlled aggregation
    ↓
Researcher result
```

Main sentence:

> **We move computation to the data instead of moving raw data to the researcher.**

---

# 14. Research Job Contract

Research execution is handled through explicit contracts.

A research job can define:
- project identity;
- algorithm identity;
- authorization reference;
- bounded data scope;
- participating node;
- execution state;
- provenance;
- controlled result.

Possible states:

```text
accepted
running
completed
empty
suppressed
denied
failed
```

`Suppressed` means:

```text
computation succeeded
but result disclosure is not allowed
```

for privacy or governance reasons.

---

# 15. SciAgents Integration

SciAgents is an important technical component.

SciAgents already exists externally.

MedDataGate does NOT reimplement it.

Instead, the Research Platform integrates SciAgents through an adapter/interface.

```text
Research Platform
        ↓
SciAgents Integration Contract
        ↓
SciAgents Adapter
        ↓
SciAgents
```

SciAgents can support scientific investigation through:
- biomedical entity resolution;
- literature analysis;
- hypothesis generation;
- contradiction search;
- evidence graphs;
- novelty checking;
- citations;
- scientific reasoning.

---

# 16. Why SciAgents Matters

Compute-to-Data answers:

> **How can we safely compute on distributed clinical data?**

SciAgents answers:

> **How can we scientifically interpret and investigate what we observe?**

The two layers are complementary.

```text
Federated clinical data
        ↓
Compute-to-Data
        ↓
Observed statistical signal
        ↓
SciAgents
        ↓
Literature investigation
        ↓
Evidence / contradictions
        ↓
Hypothesis
        ↓
Human scientific validation
```

This transforms the platform from simple data access into a scientific intelligence ecosystem.

---

# 17. Complete Research Loop

```text
Research Question
      ↓
Research Request
      ↓
Ethics / Governance Approval
      ↓
Compute-to-Data Job
      ↓
Hospital Nodes
      ↓
Controlled Result
      ↓
SciAgents
      ↓
Scientific Evidence
      ↓
Human Review
      ↓
Validated Knowledge
```

This is one of the strongest architecture messages.

---

# 18. AI Architecture Principle

AI should be treated as a replaceable technical capability.

```text
AI Services
│
├── Clinical Extraction
├── Consultation Summarization
├── Document Review
├── Lab Extraction
├── Medication Explanation
├── Priority Explanation
└── Research Assistance
```

Use ports and adapters.

```text
Application
    ↓
AI Port
    ↑
LLM Provider Adapter
```

Do not couple business logic directly to one AI provider.

---

# 19. Communication Architecture

Cross-component communication must use explicit contracts.

```text
contracts/
├── api/
├── events/
├── federation/
└── schemas/
```

Allowed:

```text
Research Platform
    ↓
Research API
    ↓
Research Service
```

Allowed:

```text
Hospital Node
    ↓
Federation Contract
    ↓
Governance Node
```

Forbidden:

```text
Research Service
    ↓
Hospital SQL database
```

Forbidden:

```text
Patient App
    ↓
Hospital database
```

---

# 20. Trust Boundaries

```text
Hospital A
    ≠
Hospital B
```

```text
Company Platform
    ≠
Ethics Authority
```

```text
Researcher
    ≠
Clinical Data Owner
```

```text
Patient App
    ≠
Hospital Database
```

```text
AI System
    ≠
Clinical Authority
```

These are core architectural invariants.

---

# 21. Main Technical Strengths

The technical strength is the combination of:

1. **Federation** — Hospitals keep local ownership.
2. **Legacy interoperability** — DMI adapters integrate existing hospital systems.
3. **Explicit governance** — Sensitive access is authorized and scoped.
4. **Patient-centric access control** — Patients can grant and revoke access.
5. **AI-assisted data capture** — Clinical information is structured earlier.
6. **Human validation** — AI does not silently become medical truth.
7. **Medication safety across providers** — Distributed history improves context.
8. **Compute-to-Data** — Research algorithms move toward the data.
9. **SciAgents** — Scientific reasoning is integrated after controlled computation.
10. **Auditability** — Sensitive operations can be traced and cryptographically anchored.

---

# 22. Technical Differentiation

Do NOT present MedDataGate as:
- another EHR;
- another hospital database;
- another medical chatbot;
- a blockchain healthcare product.

Present it as:

> **A federated intelligence, interoperability and governance layer between existing healthcare systems.**

Technically, the system combines:

```text
Legacy hospital systems
        +
Hospital-local nodes
        +
Federation
        +
Consent and governance
        +
AI-assisted care
        +
Compute-to-Data
        +
SciAgents
        +
Auditable trust
```

---

# 23. Requested Slide Structure

Create approximately **8 technical slides**.

Do not create a business slide.

## Slide 1 — Technical Problem

### Title
**Healthcare data breaks before it becomes useful**

Visual:

```text
New Service
   X
Consultation
   X
Manual Entry
   X
Separated Services
   X
Research / ML
```

Show:
- patient carries record;
- information loss;
- missing validation;
- missing synchronization;
- garbage in, garbage out.

Keep text minimal.

## Slide 2 — Repairing the Data Journey

### Title
**We repair each break in the data flow**

Use matching before/after metaphor.

Top:
broken line with red cracks.

Bottom:
healthy continuous line.

At each repair point, use a **bandage / plaster icon**.

Short labels only:

```text
Unified History
Assisted Capture
Validation
Secure Federation
Governed Research
```

Do NOT explain all features here.

## Slide 3 — Federated Architecture

### Title
**Federation instead of centralization**

Main architecture diagram:

```text
                    Governance / Ethics Node
                    Policies + Authorization
                         + Audit + Ledger
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
 Hospital Node A      Hospital Node B      Hospital Node C
       │                    │                    │
   DMI Adapter          DMI Adapter          DMI Adapter
       │                    │                    │
   Local DMI            Local DMI            Local DMI
         └────────────────────┼────────────────────┘
                              │
                         Federation
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
       Patient App      Clinician App      Research Platform
                                                │
                                                ▼
                                             SciAgents
```

Also show:

```text
Research Platform
       ↕
Governance / Ethics Node
```

for research requests / approvals.

Important visual statement:

> **Clinical data stays in hospitals.**

## Slide 4 — Hospital Node + Clinical Capture

### Title
**Improve data quality at the source**

Hospital integration:

```text
Legacy DMI
    ↓
DMI Adapter
    ↓
Hospital Node
    ↓
Canonical / FHIR Data
```

Consultation:

```text
Consultation
    ↓
Speech-to-Text
        OR
Adaptive Intake
    ↓
Structured Extraction
    ↓
Clinician Validation
```

Add:

> **AI assists. Humans validate.**

## Slide 5 — Patient + Clinician Intelligence

### Title
**One patient context across multiple care providers**

Patient timeline:

```text
Hospital A
Private Doctor
Hospital B
```

Medication example:

```text
Old medication
from Hospital A
      +
New prescription
      ↓
Interaction Warning
      ↓
Doctor Review
```

Technical messages:
- authorized longitudinal view;
- consent;
- scoped access;
- distributed medication history;
- clinician decision support.

## Slide 6 — Governance + Trust

### Title
**Sensitive access is explicit, scoped and auditable**

Around the Governance / Ethics Node:

```text
WHO?
WHAT DATA?
WHY?
HOW LONG?
WITH WHOSE CONSENT?
```

Flow:

```text
Hospital Node A
      ↓
Access Request
      ↓
Governance
      ↓
Temporary Authorization
      ↓
Hospital Node B
```

Blockchain:

```text
Audit Event
    ↓
Hash / Signature
    ↓
Immutable Ledger
```

Strong sentence:

> **Blockchain stores proofs, not patients.**

## Slide 7 — Compute-to-Data + SciAgents

### Title
**From secure computation to scientific intelligence**

```text
Researcher
    ↓
Research Project
    ↓
Ethics Request
    ↓
Governance Approval
    ↓
Research Job
    ↓
Hospital Nodes
    ↓
Local Compute-to-Data Execution
    ↓
Controlled / Aggregated Result
    ↓
SciAgents
    ↓
Literature + Evidence + Hypotheses + Contradictions
    ↓
Human Scientific Validation
```

Highlight:

### Compute-to-Data
**Move algorithms to data**

### SciAgents
**Turn results into scientific investigation**

Main statement:

> **Computation stays close to clinical data. Scientific reasoning happens on controlled outputs.**

## Slide 8 — Technical Differentiation / Closing

### Title
**Not another EHR — a federated intelligence layer**

Show technical pillars:

```text
Federation
Legacy DMI Integration
Governance
AI-Assisted Capture
Compute-to-Data
SciAgents
Auditable Trust
```

Final statement:

> **Hospitals keep the data. Governance controls access. AI improves capture. Compute moves to the data. SciAgents turns observations into scientific evidence.**

Final tagline:

> **Connect the care. Keep the data local. Move intelligence instead.**

---

# 24. Timing

Total target: about **5 minutes**.

| Slide | Time |
|---|---:|
| 1. Problem | 40 sec |
| 2. Repair | 25 sec |
| 3. Architecture | 55 sec |
| 4. Hospital Node / Capture | 45 sec |
| 5. Patient / Clinician | 40 sec |
| 6. Governance | 40 sec |
| 7. Compute-to-Data + SciAgents | 60 sec |
| 8. Differentiation | 35 sec |

---

# 25. Speaker Notes

Create concise speaker notes for every slide.

They should sound natural and technical.

Do not simply read slide text.

The notes should explain:
- why the architecture exists;
- what data moves;
- what does not move;
- where authorization happens;
- where AI intervenes;
- where humans validate;
- why Compute-to-Data matters;
- why SciAgents matters.

---

# 26. Canva Design Requirements

Use Canva MCP to build the actual deck.

Format:

**16:9**

Visual style:
- clean;
- modern;
- startup;
- technical;
- healthcare;
- architecture-focused.

Palette:

```text
Dark Navy      #0F172A
Medical Blue   #2563EB
Sky Blue       #38BDF8
Teal           #14B8A6
Green          #22C55E
Light Gray     #F8FAFC
Warning Red    #EF4444
```

Typography:

```text
Titles: Poppins Bold
Body: Inter
```

Use:
- simple icons;
- rounded cards;
- diagrams;
- arrows;
- architecture blocks;
- minimal line illustrations.

For problem/solution slides:
use an Excalidraw-like or hand-drawn visual style.

For technical architecture:
use a cleaner technical diagram style.

---

# 27. Avoid

Do NOT:
- create a business model slide;
- discuss revenue;
- discuss pricing;
- overload slides with paragraphs;
- use generic hospital stock photography;
- use blockchain as the central product message;
- portray AI as autonomous;
- imply all data is centralized;
- imply SciAgents stores clinical data;
- imply researchers receive unrestricted raw datasets;
- imply the system requires hospitals to replace their DMI.

---

# 28. Technical Accuracy Rules

The deck must preserve these invariants:

```text
Hospital data stays under Hospital Node control.
```

```text
DMI Adapter is local to the Hospital Node.
```

```text
Governance Node authorizes access.
```

```text
Company Platform != Ethics Authority.
```

```text
Blockchain contains proofs, not clinical records.
```

```text
AI assists; humans validate.
```

```text
Research prefers Compute-to-Data.
```

```text
SciAgents is integrated, not reimplemented.
```

```text
Federation does not equal centralization.
```

---

# 29. Final Objective

The jury should understand these 5 technical ideas after the presentation:

1. **We improve the quality of healthcare data from the moment it is captured.**

2. **Hospitals keep their existing systems and retain local control of clinical data.**

3. **Federation and governance allow controlled cross-institution access without building one giant clinical database.**

4. **Compute-to-Data allows research without unrestricted raw-data export.**

5. **SciAgents adds a scientific reasoning layer on top of controlled research results, connecting distributed clinical evidence with literature, hypotheses and human validation.**

Create the final Canva deck with these principles.
