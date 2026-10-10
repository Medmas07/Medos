# Governance Portal

## Purpose and status

- **IMPLEMENTED (D1):** Governance Portal shell (HC-070, [#71](https://github.com/Medmas07/Hackcure_hackathon/issues/71)) and Governance dashboard (HC-071, [#72](https://github.com/Medmas07/Hackcure_hackathon/issues/72)) at initial depth D1. Built with React 19 + TypeScript + Vite SPA as decided in [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md) and styled with Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)).
- **Checked on 2026-10-10:** `npm run build`, `npm run lint`, and `npm test` (Vitest suite covering canonical demo-data loading, dashboard metrics calculation, federated nodes status, hash verification, and state behavior) all pass. Fixed dev port is `5174`.
- **Mocking strategy:** Consumes canonical fictional fixtures from `demo-data/` ([ADR-0005](../../../docs/decisions/ADR-0005-canonical-demo-data.md)). Simulated local ledger proofs (SHA-256) and advisory AI annotations are explicitly marked with `DemoBanner` and `DemoBadge`. No direct access to hospital clinical databases.

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
