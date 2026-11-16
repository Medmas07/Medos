# Prompt Claude + Canva MCP — MedDataGate Business Pitch (3 minutes)

You are creating a **3-minute startup / hackathon business pitch deck** in Canva for **MedDataGate**, a federated healthcare data and intelligence ecosystem.

Use Canva MCP to create the presentation directly.

The Business Model slides already exist and must NOT be recreated. This generated section should end with a transition into those slides.

The challenge is:

> **Do not neglect any important product capability, but compress the story enough to fit approximately 3 minutes.**

That means:
- group related features;
- avoid one slide per feature;
- use visual clusters and short labels;
- preserve the strongest technical differentiators;
- make every feature answer a previously shown problem;
- keep speaker notes concise enough for the timing.

---

# Product positioning

## MedDataGate

**Federated Healthcare Data & Intelligence Ecosystem**

Core message:

> **Connect the care. Keep the data local. Move intelligence instead.**

MedDataGate connects:
- patients;
- clinicians;
- hospitals;
- researchers;
- governance / ethics authorities;

without requiring all clinical data to be copied into one giant centralized database.

---

# Story arc

Build the deck as one continuous story:

```text
REAL EXPERIENCE
      ↓
BROKEN DATA JOURNEY
      ↓
REPAIR THE BREAKS
      ↓
CLINICAL + PATIENT INTELLIGENCE
      ↓
FEDERATION + GOVERNANCE
      ↓
ETHICS + LEGAL SAFEGUARDS
      ↓
COMPUTE-TO-DATA + SCIAGENTS
      ↓
VALUE FOR ALL ACTORS
      ↓
BUSINESS MODEL
```

Do NOT present a random catalog of technologies.

Use this narrative:

> **Problem → Repair → Capability → Value**

---

# Slide 1 — Storytelling

## Title

**It starts with situations we have all seen.**

Use a simple patient journey:

```text
Patient
   ↓
Doctor
   ↓
Hospital
   ↓
Laboratory
   ↓
Specialist
```

Show that each transition creates friction:

- patient carries documents;
- same questions are repeated;
- consultation information may not become structured data;
- services are poorly synchronized;
- manual entry happens under pressure.

Speaker direction:

> “MedDataGate did not start from a technology. It started from situations we kept seeing: a patient repeating the same history, carrying documents from one doctor to another, while different services reconstruct the same information again and again.”

Target: **20 sec**

---

# Slide 2 — The broken data workflow

## Title

**Healthcare data breaks before it becomes useful.**

Use one horizontal broken line:

```text
New Doctor
   X
Consultation
   X
Manual Entry
   X
Separated Services
   X
Research / ML
```

At each break, only one short problem:

1. **Patient carries the history**
2. **Information is lost during consultation**
3. **Manual entry is not always validated**
4. **Services repeat information and do not synchronize**
5. **Researchers inherit low-quality data**

Around the final database, show only:
- missing;
- duplicated;
- inconsistent;
- aberrant.

End with:

> **Garbage in, garbage out.**

Speaker direction:

> “The poor research dataset is not created at the research stage. It accumulates progressively throughout the patient journey.”

Target: **25 sec**

---

# Slide 3 — Repairing the breaks

## Title

**MedDataGate repairs every break in the data journey.**

Use the exact same geometry as Slide 2.

### Before

```text
────X────X────X────X────X────>
```

### After

Use one continuous line with **bandage / plaster icons** exactly at the old break positions:

```text
────🩹────🩹────🩹────🩹────🩹────>
```

Use only five short labels:

1. **Unified History**
2. **Assisted Capture**
3. **Human Validation**
4. **Secure Federation**
5. **Governed Research**

Bottom sentence:

> **We do not simply centralize data — we repair the entire data journey.**

Target: **15 sec**

---

# Slide 4 — Clinical + Patient Intelligence

## Title

**Better data starts during care.**

Group all patient and clinician capabilities into **three compact visual clusters**.

## Cluster A — Patient continuity

Show a mobile timeline with:

```text
Hospital A
Private Doctor
Hospital B
```

Represent these features visually with small icons, not paragraphs:

- unified longitudinal history;
- hospital history;
- physician history;
- medication history;
- laboratory results;
- consent management;
- grant doctor access;
- revoke access;
- trusted family delegation;
- restriction / digital erasure request;
- notifications.

Main value:

> **The patient no longer has to reconstruct their medical story manually.**

## Cluster B — Assisted consultation

Show:

```text
Consultation
     ↓
Patient Consent
     ↓
Speech-to-Text
     ↓
AI Extraction
     ↓
Structured Draft
     ↓
Clinician Validation
```

Alternative:

```text
No recording
     ↓
Adaptive Intake
```

Capabilities to represent:
- speech-to-text;
- adaptive intake;
- consultation summarization;
- clinical extraction;
- lab-value extraction;
- structured notes;
- missing-information detection;
- human validation.

Core line:

> **AI assists. Humans validate.**

## Cluster C — Clinical safety + priority

Medication flow:

```text
Old Medication
from Hospital A
      +
New Prescription
      ↓
Potential Interaction
      ↓
Doctor Review
```

Use the concept:
- distributed medication history;
- validated interaction rules;
- patient context;
- LLM explanation;
- clinician decision.

Also show:

```text
Patient Events
      ↓
Priority Engine
      ↓
Clinician Queue
```

Capabilities:
- abnormal result alerts;
- medication warnings;
- follow-up alerts;
- notification center;
- LLM-assisted priority explanation.

Do not imply that the LLM independently prescribes or performs autonomous critical triage.

Target: **40 sec**

---

# Slide 5 — Federation + Governance + Blockchain

## Title

**Connect hospitals without replacing their systems.**

Use one compact architecture:

```text
                    Governance / Ethics Node
                    Authorization + Audit
                          + Blockchain
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
 Hospital Node A        Hospital Node B        Hospital Node C
        │                      │                      │
   DMI Adapter             DMI Adapter             DMI Adapter
        │                      │                      │
   Legacy DMI              Legacy DMI              Legacy DMI
        └──────────────────────┼──────────────────────┘
                               │
                          Federation
                               │
          Patient App • Clinician App • Research Platform
```

## Hospital Node

Visually represent:
- local clinical data;
- local API;
- identity / RBAC;
- consent enforcement;
- audit generation;
- federation client;
- canonical / FHIR representation;
- health checks;
- local DMI adapter.

Important:

> **The hospital keeps its existing DMI/HIS.**

There is no central DMI service.

## Hospital onboarding

Include this in a compact callout or speaker notes:

```text
Registration
→ documents
→ agreements
→ technical + DMI questionnaire
→ automated / LLM-assisted review
→ human validation
→ configured Hospital Node package
→ node health/status
```

## Governance / Ethics Node

Show five short questions:

```text
WHO?
WHAT?
WHY?
HOW LONG?
WITH WHOSE CONSENT?
```

Represent:
- hospital approval;
- synchronization authorization;
- research authorization;
- consent / policy evaluation;
- temporary access;
- audit.

Important trust boundary:

> **Company Platform ≠ Ethics Authority**

## Blockchain

Use a small supporting icon, not the central visual.

Main statement:

> **Blockchain stores proofs, not patients.**

Ledger may contain:
- authorization IDs;
- event hashes;
- timestamps;
- signatures;
- versions.

Never:
- diagnoses;
- prescriptions;
- lab reports;
- patient files;
- medical images;
- raw FHIR records.

Target: **40 sec**

---


# Slide 6 — Éthique, consentement & cadre légal tunisien

## Title

**Ethics by design — le patient garde le contrôle**

This slide must remain visually simple. Do NOT turn it into a legal-text slide.

Use a central **Patient + Consent** visual, surrounded by 4 short principles.

### 1. Consentement & contrôle du patient

Ethical product principle:

> **No optional / secondary use of a patient's health data is initiated without an explicit authorization path.**

Show:
- granular consent;
- grant access;
- revoke access;
- purpose / scope;
- duration;
- trusted family delegation;
- request for restriction / erasure where legally applicable.

Important nuance:
Do NOT claim that Tunisian law requires patient consent for absolutely every possible health-data treatment. Present explicit patient control as a **stronger product-level ethical design choice**, while acknowledging that Tunisian law also recognizes other legal bases for health-data processing in specific cases.

### 2. Loi organique tunisienne n° 2004-63

Use a small law / shield icon.

Mention only the main points relevant to the product:

- health data is treated as sensitive / specially protected personal data;
- explicit consent is one legal basis for processing health data;
- health-data processing is subject to specific safeguards;
- the platform must respect purpose limitation, authorization and security requirements;
- cross-border transfers require legal safeguards / authorization conditions.

Do not overload the slide with article numbers. If useful, put **Art. 14 & Art. 62** only in a small footer or speaker note.

### 3. Data minimization + local hospital control

Show:

```text
Hospital Node
   ↓
Local clinical data

Algorithm / authorized request
   ↓
goes toward the node
```

Message:

> **Data stays close to the hospital; only authorized access or controlled results move.**

This supports:
- minimization;
- reduced unnecessary copying;
- stronger institutional control;
- Compute-to-Data.

Do NOT claim that this architecture automatically guarantees legal compliance.

### 4. Governance + auditability

Show:

```text
Request
  ↓
Governance / Ethics Node
  ↓
Policy + Consent Check
  ↓
Temporary Authorization
  ↓
Audit Proof
```

Represent:
- who;
- what;
- why;
- for how long;
- consent / legal basis;
- audit trail.

Blockchain remains only an audit-proof mechanism:

> **Blockchain stores proofs, not patients.**

### Tunisia / international alignment callout

Add a small footer:

**Tunisia: Law 2004-63 + Convention 108**

The presentation may mention that Tunisia has been Party to **Convention 108 since 1 November 2017** and signed the modernized **Convention 108+ protocol in 2019**.

Do NOT claim equivalence with GDPR.
Use wording like:

> **Aligned with internationally recognized data-protection principles.**

### Critical legal accuracy rule

Do NOT state that the Governance / Ethics Node replaces the INPDP or any public regulator.

The Governance Node is an **internal technical and organizational control layer** for:
- consent enforcement;
- policy checks;
- authorization workflows;
- auditability.

It does not substitute for legally required regulatory authorization or oversight.

Do NOT claim “fully compliant” unless a formal legal review has been completed.

### Speaker direction

> “We designed ethics into the architecture, not as an afterthought. The patient gains granular control over access, hospitals keep clinical data locally, and every sensitive access can be scoped, authorized and audited. Our design is aligned with Tunisia’s personal-data framework, particularly Law 2004-63, while our governance layer supports — but does not replace — the competent legal authority.”

Target: **20–25 sec**

---

# Slide 7 — Research Innovation: Compute-to-Data + SciAgents

## Title

**Move the algorithm, not the data. Then add scientific intelligence.**

Split this slide into two connected layers.

## Layer 1 — Compute-to-Data

Cross out the traditional model:

```text
Hospital Data
      ↓
Raw Export
      ↓
Researcher Laptop
```

Then show:

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
Local Execution
    ↓
Controlled / Aggregated Result
```

Main message:

> **The algorithm goes to the data. The raw data does not need to leave the hospital.**

Research capabilities that must be represented somewhere on the slide or in speaker notes:

- researcher onboarding;
- project creation;
- protocol upload;
- cohort definition;
- variable selection;
- participating hospital selection;
- ethics request;
- request status;
- Colab-like notebook;
- Python/research workspace concept;
- distributed research job execution;
- execution status;
- controlled / aggregated outputs;
- experiment history.

Small technical callout for research job states:

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

> computation succeeded, but disclosure of the result is not authorized.

Do not make this the dominant visual.

## Layer 2 — SciAgents

SciAgents already exists externally.

MedDataGate **integrates it; it does not reimplement it**.

Context:

The project integrates the ideas and implementation around:

**“SciAgent: A Unified Multi-Agent System for Generalistic Scientific Reasoning.”**

Show:

```text
Controlled Research Result
        ↓
SciAgents
        ↓
Literature
Evidence
Hypotheses
Contradictions
Citations
Novelty
        ↓
Human Researcher
```

Represent these capabilities:

- biomedical entity resolution;
- literature analysis;
- evidence retrieval;
- hypothesis generation;
- contradiction search;
- evidence graphs;
- novelty analysis;
- citations;
- scientific reasoning.

Key distinction:

> **Compute-to-Data answers: how do we safely compute on distributed clinical data?**

> **SciAgents answers: how do we scientifically investigate what the result means?**

Strong line:

> **We do not stop at data access — we connect clinical evidence to scientific reasoning.**

Target: **45 sec**

---

# Slide 8 — Stakeholder Value

## Title

**One ecosystem, five winners.**

Use exactly five cards.

Keep each card visually simple: one sentence + 2–3 icons.

## Patient

Show:
- timeline;
- consent;
- family access.

Message:

> **My medical history follows me, and I control important access to it.**

## Clinician

Show:
- longitudinal context;
- AI documentation;
- medication warning;
- priority queue.

Message:

> **I make decisions with better context and less documentation friction.**

## Hospital

Show:
- existing DMI;
- Hospital Node;
- federation.

Message:

> **I connect without replacing my systems or giving up control of my data.**

## Researcher

Show:
- notebook;
- distributed compute;
- SciAgents.

Message:

> **I can work with distributed clinical evidence without simply downloading raw patient datasets.**

## Governance / Ethics

Show:
- authorization;
- consent;
- audit / ledger.

Message:

> **I can control and trace who accesses what, why, and for how long.**

Bottom transition:

> **The same infrastructure creates value for every actor. The next question is how we scale it sustainably.**

Then transition to the already-prepared Business Model slides.

Target: **25 sec**

---

# Features that must NOT be omitted

Even if they are grouped visually or placed in speaker notes, cover all of these:

## Patient
- unified longitudinal history;
- hospital history;
- physician history;
- medications;
- labs;
- consent management;
- grant doctor access;
- revoke access;
- family/caregiver delegation;
- restriction / erasure request;
- notifications.

## Clinician
- dashboard;
- authorized patient list;
- federated patient history;
- consultation workspace;
- speech-to-text;
- adaptive intake;
- AI clinical extraction;
- lab extraction;
- consultation summarization;
- medication safety;
- alerts;
- intelligent priority queue;
- LLM-assisted priority explanation.

## Hospital
- onboarding portal;
- registration;
- document upload;
- agreements;
- technical questionnaire;
- DMI/HIS questionnaire;
- automated / LLM-assisted review;
- human approval;
- configured Hospital Node;
- downloadable instance package;
- deployment / health status;
- local DMI adapter;
- canonical / FHIR representation;
- local data control.

## Ethics & Legal
- explicit, granular patient consent for optional / secondary uses;
- grant / revoke access;
- purpose, scope and duration of access;
- local-data / minimization principle;
- Tunisian Organic Law No. 2004-63;
- health-data-specific protections;
- cross-border transfer constraints;
- Convention 108 alignment;
- governance layer does not replace INPDP / competent authority;
- no “fully compliant” claim without formal legal review.

## Governance
- hospital approval;
- synchronization requests;
- research access requests;
- consent / policy evaluation;
- temporary authorization;
- audit timeline;
- blockchain proofs.

## Research
- researcher onboarding;
- projects;
- protocol upload;
- cohort definition;
- variable selection;
- hospital selection;
- ethics requests;
- request status;
- notebook / Colab-like workspace;
- Compute-to-Data;
- distributed execution;
- controlled results;
- experiment history;
- SciAgents.

## AI
- clinical extraction;
- consultation summarization;
- hospital document review;
- lab extraction;
- medication explanation;
- queue-priority explanation;
- research assistance.

## Trust / Architecture
- Hospital Nodes;
- DMI adapter local to Hospital Node;
- federation;
- explicit contracts;
- Governance / Ethics Node;
- patient consent;
- no direct cross-component SQL access;
- no central clinical database;
- blockchain proof-only design;
- clinical data remains under hospital control.

Do NOT create separate slides for all these items.

Compress intelligently.

---

# 3-minute timing

Target approximately **3 minutes** total before the existing Business Model slides.

| Slide | Time |
|---|---:|
| 1. Storytelling | 18 sec |
| 2. Broken workflow | 22 sec |
| 3. Repair | 12 sec |
| 4. Clinical + Patient Intelligence | 34 sec |
| 5. Federation + Governance | 32 sec |
| 6. Ethics + Legal | 22 sec |
| 7. Compute-to-Data + SciAgents | 38 sec |
| 8. Stakeholder Value | 22 sec |

Speaker notes must respect this timing.

Use approximately 35–80 spoken words per slide depending on allocated time.

---

# Canva design requirements

Use Canva MCP to build the actual slides.

## Format

16:9

## Style

Modern healthcare startup.

Use:
- storytelling illustrations;
- Excalidraw-like problem/solution diagrams;
- clean UI cards;
- minimal architecture diagrams;
- icon-based feature clusters.

Avoid:
- dense paragraphs;
- generic hospital stock photography;
- unnecessary animations;
- one feature per slide.

## Color language

- Blue → healthcare / technology
- Teal → federation / data
- Green → repaired / approved / validated
- Purple → research / SciAgents
- Red / Orange → problems / warnings

Suggested palette:

```text
Dark Navy    #0F172A
Blue         #2563EB
Sky          #38BDF8
Teal         #14B8A6
Green        #22C55E
Purple       #7C3AED
Light Gray   #F8FAFC
Red          #EF4444
Orange       #F97316
```

Typography:

```text
Titles: Poppins Bold
Body: Inter
```

---

# Technical accuracy rules

Never claim:
- all clinical data is centralized;
- blockchain stores patient records;
- an LLM autonomously diagnoses;
- an LLM autonomously prescribes;
- an LLM is the only medication-safety mechanism;
- an LLM is the sole critical triage mechanism;
- SciAgents stores raw hospital data;
- SciAgents is reimplemented inside MedDataGate;
- researchers freely download unrestricted clinical datasets;
- hospitals must replace their DMI;
- the company itself is the Ethics Authority.

Always preserve:

> **Hospital data stays under Hospital Node control.**

> **DMI Adapter is local to each Hospital Node.**

> **Governance authorizes sensitive access.**

> **AI assists; humans validate.**

> **Blockchain stores proofs, not patients.**

> **Research prefers Compute-to-Data.**

> **SciAgents is integrated as a scientific reasoning layer.**

---

# Speaker-note style

The notes should sound like a founder explaining a real problem, not reading bullets.

Suggested transitions:

### Opening

> “MedDataGate did not start from a technology. It started from situations we kept seeing: patients repeating the same history and carrying information from one provider to another.”

### Problem → Solution

> “Each situation looks small on its own. Together, they break the lifecycle of the data. So instead of adding another database, we decided to repair each break.”

### Clinical → Federation

> “Better capture is not enough if hospitals remain isolated. The next repair is interoperability without forcing hospitals to replace what they already use.”

### Federation → Research

> “Once hospitals can collaborate without giving up control of their data, research becomes possible in a completely different way.”

### Compute-to-Data → SciAgents

> “Secure computation gives us a result. SciAgents helps us investigate what that result means scientifically.”

### Transition to Business Model

> “The same infrastructure creates value for patients, clinicians, hospitals, researchers and governance. The next question is how we make that ecosystem sustainable.”

---

# Final objective

At the end of these 3 minutes, the jury should remember:

1. **Healthcare data quality breaks throughout the patient journey.**
2. **MedDataGate repairs those breaks from capture to research.**
3. **Hospitals keep existing systems and retain local data control.**
4. **AI improves capture and assistance while humans remain responsible.**
5. **Federation and governance enable controlled interoperability.**
6. **Blockchain adds traceability without storing clinical records.**
7. **Compute-to-Data moves algorithms toward data instead of exporting raw datasets.**
8. **SciAgents turns controlled research outputs into scientific investigation.**
9. **Patients, clinicians, hospitals, researchers and governance all gain value from the same ecosystem.**

Create the Canva deck so all of this is communicated clearly without exceeding the 3-minute target.
