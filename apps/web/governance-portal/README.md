# Governance Portal

## Purpose and status

PLANNED web product for the Governance / Ethics Authority. Its technology (React + TypeScript + Vite SPA) is CONFIRMED by [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md); no UI code exists yet, and scaffolding belongs to HC-070. Development commands (`npm run dev`, `npm run build`, `npm run lint`, `npm run preview`) and the scaffold procedure are recorded in that ADR. Styling uses Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)); wiring it in also belongs to HC-070.

## Responsibilities and owned concepts

- Review views for hospital, synchronization, and research requests.
- Policy/consent-governance context, governance audit exploration, and proof verification.
- Presentation of Governance Node decisions and alerts.

## Communication boundaries

The portal will communicate through Governance Node APIs/contracts and never through direct persistence access.

## Non-responsibilities

It is not a company self-approval surface, a clinical-record editor, a research executor, or a blockchain database.

## Expected contracts

PLANNED governance work queues, decision requests/responses, audit-event views, and minimized ledger-proof views.
