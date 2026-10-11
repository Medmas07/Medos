# Hospital Portal

## Purpose and status

Hospital dashboard for the day-to-day administration of one establishment, with two pages: **Gestion du personnel** and **Gestion des patients**. It is a new app, not the onboarding portal that used to live at this path; that one moved to [`apps/web/landing/`](../landing/README.md) ([ADR-0012](../../../docs/decisions/ADR-0012-medos-landing-and-hospital-journey.md)). React 19 + TypeScript + Vite SPA per [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md), styled with Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)).

- **IMPLEMENTED, MOCKED data:** both pages, for the fictional Hôpital Universitaire Bab Ennour (`org-hospital-a`) from the canonical [demo data](../../../demo-data/README.md) ([ADR-0005](../../../docs/decisions/ADR-0005-canonical-demo-data.md)), read in the browser. Every change stays in browser memory and is lost on reload. There is no API, persistence, or authentication.
- **Gestion du personnel** (`#personnel`): the hospital's fictional clinicians with role, specialty or service, and status; counts of active staff, physicians, and nurses; search and role filter; add a member (validated) and deactivate or reactivate one. Adding a member creates no account and grants no access.
- **Gestion des patients** (`#patients`): **administrative identity only** (local identifier "IPP", name, sex, birth date and age, city) for the fictional patients holding an identifier at this hospital. There are no clinical data on this page; a test pins the exposed fields. Search by IPP, name, or city; registering a patient validates the form (real date, not in the future) and assigns the next IPP of the year (`BEN-<year>-<5 digits>`).
- **Checked on 2026-10-11:** `npm run build`, `npm run lint`, and `npm test` (10 tests: hospital fixture, staff loading for this hospital only, validation, add, deactivate, filters; patient loading with the local identifier, administrative fields only, validation, IPP sequence, age, search) pass. The served build was driven in headless Chromium: deactivating a member, the patient form's validation errors, then registering a patient that appears with `BEN-2026-00001`, and the 390 px layout; no page errors and no non-GET request.

OPEN: whether this dashboard becomes the local user interface of the Hospital Node (data served by the Node's own API) or stays a separate product. Until decided, it reads only the fictional fixtures and connects to nothing.

## Commands

From inside `apps/web/hospital-portal/` (run `npm install` in [`design-system/`](../../../design-system/README.md) once as well):

| Purpose | Command |
|---|---|
| Install dependencies | `npm install` |
| Dev server on <http://localhost:5176> | `npm run dev` |
| Type-check and production build | `npm run build` |
| Lint | `npm run lint` |
| Unit tests | `npm test` |
| Preview the build | `npm run preview` |

## Responsibilities

- Display and local, in-memory management of the establishment's staff list.
- Display and local, in-memory registration of patients' administrative identity.

## Non-responsibilities

It does not show or edit clinical records, create accounts or access rights, connect to a DMI/HIS or a hospital database, or exchange data with other hospitals.
