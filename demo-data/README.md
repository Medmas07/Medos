# Demo Data

## Purpose and status

Canonical **fictional** dataset reused by every product for the [canonical demo](../docs/planning/demo-scenario.md), delivered by HC-005 ([#28](https://github.com/Medmas07/Hackcure_hackathon/issues/28)) at depth D1. Location and format are decided in [ADR-0005](../docs/decisions/ADR-0005-canonical-demo-data.md).

- **IMPLEMENTED:** language-neutral JSON fixtures and a standard-library integrity checker.
- **Checked on 2026-10-10:** `python demo-data/check_fixtures.py` passes. Deliberately broken copies (unknown reference, cross-organization authorship, clinical field in a ledger proof, tampered proof, expired demo grant, missing fictional marker) all fail with a precise message. A temporary Vite portal at `apps/web/<portal>/` depth imported the JSON with type inference in `tsc -b`, `vite build`, and `vite dev` with no extra configuration. Python consumption works: the Federation Service's simulated Hospital Nodes read the records, grants, and decisions (HC-141), and each Hospital Node instance loads its own records file into its mock clinical repository (HC-113). Flutter consumption is untested.

Everything here is **MOCKED / fictional**: people, organizations, medicines, the interaction rule, AI transcripts and extractions, priority scores, research results, SciAgents output, and ledger proofs. Any resemblance to real people or establishments is coincidental. Never use this data for clinical decisions, and never add real data.

## Contents

| File | Owner it represents | Contents |
|---|---|---|
| [`manifest.json`](manifest.json) | — | Dataset version, reference date (`2026-10-10`, UTC+01:00), file list, and **scenario roles** mapping demo names ("Patient A", "Dr. X", "Medication A") to ids. |
| [`organizations.json`](organizations.json) | Registry view | Hospitals A, B, C (C is in onboarding), a private practice, the Governance / Ethics Authority, the platform operator, a research lab; node status for approved organizations. |
| [`people.json`](people.json) | Identity view | Three patients with per-organization local identifiers, a trusted relative, physicians and nurses, a hospital manager, a governance reviewer, a researcher. |
| [`records/hospital-a.json`](records/hospital-a.json), [`records/hospital-b.json`](records/hospital-b.json), [`records/private-practice.json`](records/private-practice.json) | Each Hospital Node | Encounters, medications, and lab reports **held by that organization only**, written by its own clinicians. |
| [`medication-rules.json`](medication-rules.json) | Medication safety | Invented medicines and one deterministic, invented interaction rule (`validated: false`). |
| [`access.json`](access.json) | Patient access | Access grants (active, expired, revoked), a family delegation, a restriction request. |
| [`governance.json`](governance.json) | Governance Node | Hospital applications (Hospital C's includes an administrative profile without a security contact, typed documents with the insurance certificate missing, and two accepted, versioned agreements), synchronization and research-access requests, decisions, minimized audit events, simulated ledger proofs (hashes verifiable). |
| [`research.json`](research.json) | Research Portal / Service | Projects, a notebook, a compute-to-data job with per-hospital stages, a controlled aggregated result, a SciAgents investigation fixture with fictional citations. |
| [`clinician.json`](clinician.json) | Clinician view | Appointments, alerts, a deterministic mocked priority queue, and the demo consultation script (transcript, extraction draft pending review, planned prescription). |
| [`notifications.json`](notifications.json) | Notifications | Notifications for patients, a relative, clinicians, governance, hospital, and research users. |

The split mirrors ownership: clinical records live in the file of the organization that holds them, never in a central file. A Patient App timeline is the combination of authorized views from several record files, as federation would produce.

### Conventions

- JSON keys and status codes are English (`status: "pending"`); display text is French (`fr-TN`). Products translate codes to labels.
- Ids are stable, readable strings (`pat-a`, `org-hospital-b`), unique across all files. Fields ending in `Id`/`Ids` reference them; medicines are referenced by `medicationCode`.
- Date-times are ISO 8601 with offset (`2026-10-10T09:00:00+01:00`); dates are `YYYY-MM-DD`.
- Every file has `"fictional": true` and a `notice`.
- These files are **not contracts**. API shapes are defined under [`contracts/`](../contracts/README.md) by HC-110 and later tickets; mock APIs (HC-115 to HC-117) should serve this data through those contracts.

## Canonical scenario

| Demo step | Data |
|---|---|
| Patient A's history across Hospital A, a private doctor, Hospital B | `pat-a` records in all three `records/` files |
| Patient A grants Dr. X scoped, temporary access | `grant-a-drx` (Patient App may show it as just created) |
| Consultation, recording consent, transcript, extraction | `script-a-2026-10-10` in `clinician.json` |
| Dr. X prescribes Medication B; conflict with Medication A from Hospital B | planned `MED-DOLORANE` vs active `med-b-leila-coagulix`, rule `rule-coagulix-dolorane` |
| Hospital onboarding with automated, assisted, and human review | `app-hospital-c` |
| Synchronization request A ↔ B, approval, audit, simulated proof | `sync-001` (starts `pending`); examples `dec-sync-002`, `evt-003`, `proof-003` |
| Research project, governance approval, compute-to-data, controlled result, SciAgents | `proj-001`, `rar-001`, `job-001`, `res-001`, `inv-001`; `proj-002` is under review |

**Known divergence:** the MOCKED AI extractor in [`services/ai/`](../services/ai/README.md) (HC-152) was written before this dataset and recognises its own English transcript (headache, fever, "Medication A"), not `script-a-2026-10-10`. Until a follow-up aligns it, the Clinician App demo and the AI service tell different consultation stories. The [medication-safety contract](../contracts/api/medication-safety/medication-safety-check.v1.yaml) examples use the generic role names; map them through `scenarioRoles`.

The demo creates new state at runtime (the new consultation, the step-20 approval, a new research project). Products keep that state locally until the Milestone 2 mock APIs exist.

## Commands

From the repository root, with Python 3.10 or later and no dependencies:

| Purpose | Command |
|---|---|
| Check references, ownership, dates, proofs, and scenario invariants | `python demo-data/check_fixtures.py` |
| Print expected ledger-proof hashes after editing an anchored payload | `python demo-data/check_fixtures.py --print-proof-hashes` |

Run the checker after every change; it exits with status 1 and lists each problem.

## Using the data

- **Web portals (Vite):** import the JSON by relative path, for example `import people from '../../../../demo-data/people.json'` from `apps/web/<portal>/src/`. TypeScript infers the types.
- **Python runtimes:** read the files with `json` relative to the repository root, in test fixtures or mock adapters only, never in Domain code.
- **Flutter apps:** OPEN. Flutter assets must live inside the app package, so HC-010 and HC-030 decide whether to copy the needed files at build time or read them another way.

## Changing the data

Keep every value fictional and coherent with the scenario. Add records to the file of the organization that holds them. Do not put patient or clinical fields in ledger proofs, audit events, or `organizations.json`. Bump `datasetVersion` in the manifest when changing ids or shapes that products depend on.
