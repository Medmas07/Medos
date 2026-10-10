# Research Portal

## Purpose and status

Company-managed web product for governed research workflows. React 19 + TypeScript + Vite SPA per [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md), styled with Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)).

- **IMPLEMENTED (D1):** the portal shell, HC-090 ([#82](https://github.com/Medmas07/Hackcure_hackathon/issues/82)). Its sidebar groups the pages into projects and requests (dashboard, new project, protocol and documents, population, variables, participating hospitals, access request, request status), Compute-to-Data (workspace, executions, controlled results), and SciAgents. The home page lists the researcher's projects with their participating hospitals, access-request status, and Governance decision, states the Compute-to-Data boundary (code goes to the data; only controlled aggregate results come back), and shows notifications. It also shows loading, empty, and error states.
- **PLANNED:** each page other than the home page is a placeholder that names its ticket (HC-091 to HC-102). Compute-to-Data pages are shown as locked unless one of the researcher's projects holds a Governance approval that is still valid.
- **MOCKED:** `src/services/researchService.ts` reads the canonical fictional fixtures ([`demo-data/`](../../../demo-data/README.md), [ADR-0005](../../../docs/decisions/ADR-0005-canonical-demo-data.md)) in the browser with a simulated 400 ms delay. The signed-in identity is the fictional researcher Dr Aymen Rezgui (`usr-aymen`, `org-research-lab`); there is no authentication. Governance decisions are displayed only. Nothing is executed, and no Research Service, Hospital Node, or SciAgents is contacted; no Research Service or research-job contract exists yet. Every page carries a `DemoBanner`.
- **Checked on 2026-10-10:** `npm run build`, `npm run lint`, and `npm test` (Vitest: fixture loading and Governance decision join, page order, Compute-to-Data locking by decision validity, demo scenarios, non-researcher identity refused) pass. The built portal was served with `npm run preview` and rendered in headless Chrome: home page, an available placeholder, a locked Compute-to-Data page, the empty and error scenarios, and a 360px-wide layout.

## Commands

From inside `apps/web/research-portal/` (run `npm install` in [`design-system/`](../../../design-system/README.md) once as well):

| Purpose | Command |
|---|---|
| Install dependencies | `npm install` |
| Dev server on <http://localhost:5175> | `npm run dev` |
| Type-check and production build | `npm run build` |
| Lint | `npm run lint` |
| Unit tests | `npm test` |
| Preview the build | `npm run preview` |

Demo scenarios: append `?demo=vide` (no research project) or `?demo=erreur` (simulated service failure) to the URL. Pages are addressed by hash, for example `#request-status` or `#workspace`.

## Responsibilities and owned concepts

- Researcher onboarding/subscription display, projects, protocols, requested cohorts/variables, and request status.
- Colab-like interface, Compute-to-Data job visualization, controlled results, and SciAgents access.

## Communication boundaries

The portal will use Research Service, Governance, job, and SciAgents Integration contracts. It never connects directly to hospital databases.

## Non-responsibilities

It does not grant ethics approval, export unrestricted raw clinical data, execute inside hospitals itself, or implement SciAgents.

## Expected contracts

PLANNED project/request, governance-status, research-job, controlled-result, and SciAgents request/response contracts.
