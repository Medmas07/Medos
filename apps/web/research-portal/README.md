# Research Portal

## Purpose and status

PLANNED company-managed web product for governed research workflows. Its web technology (React + TypeScript + Vite SPA) is CONFIRMED by [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md); no UI, notebook runtime, or execution code exists yet, and scaffolding belongs to HC-090. Development commands (`npm run dev`, `npm run build`, `npm run lint`, `npm run preview`) and the scaffold procedure are recorded in that ADR. Styling uses Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)); wiring it in also belongs to HC-090.

## Responsibilities and owned concepts

- Researcher onboarding/subscription display, projects, protocols, requested cohorts/variables, and request status.
- Colab-like interface, Compute-to-Data job visualization, controlled results, and SciAgents access.

## Communication boundaries

The portal will use Research Service, Governance, job, and SciAgents Integration contracts. It never connects directly to hospital databases.

## Non-responsibilities

It does not grant ethics approval, export unrestricted raw clinical data, execute inside hospitals itself, or implement SciAgents.

## Expected contracts

PLANNED project/request, governance-status, research-job, controlled-result, and SciAgents request/response contracts.
