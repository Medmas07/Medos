# Hospital Portal

## Purpose and status

PLANNED company-managed web product for hospital onboarding. Its technology (React + TypeScript + Vite SPA) is CONFIRMED by [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md); no UI code exists yet, and scaffolding belongs to HC-050. Development commands (`npm run dev`, `npm run build`, `npm run lint`, `npm run preview`) and the scaffold procedure are recorded in that ADR.

## Responsibilities and owned concepts

- Registration submissions, administrative documents, agreements, and technical questionnaires.
- Display of completeness, assisted-review, human-review, and approval states.
- Display of generated Hospital Node configuration, package guidance, and operational status.

## Communication boundaries

The portal will use explicit APIs/contracts to onboarding services and display Governance Node decisions. It must not access governance or hospital databases directly.

## Non-responsibilities

It does not approve hospitals, own clinical data, connect to hospital DMI/HIS systems, or install privileged software silently.

## Expected contracts

PLANNED onboarding submission, document metadata, technical questionnaire, approval-status, Node-configuration, package, and health-status contracts.
