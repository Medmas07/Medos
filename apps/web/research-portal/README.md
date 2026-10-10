# Research Portal

## Purpose and status

Company-managed web product for governed research workflows. React 19 + TypeScript + Vite SPA per [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md), styled with Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)).

- **IMPLEMENTED (D1):** the portal shell, HC-090 ([#82](https://github.com/Medmas07/Hackcure_hackathon/issues/82)). Its sidebar groups the pages into projects and requests (dashboard, new project, protocol and documents, population, variables, participating hospitals, access request, request status), Compute-to-Data (workspace, executions, controlled results), and SciAgents. The home page lists the researcher's projects with their participating hospitals, access-request status, and Governance decision, states the Compute-to-Data boundary (code goes to the data; only controlled aggregate results come back), and shows notifications. It also shows loading, empty, and error states.
- **IMPLEMENTED (D1):** the researcher dashboard, HC-091 ([#83](https://github.com/Medmas07/Hackcure_hackathon/issues/83)), at `#dashboard`. It counts projects, requests under Governance review, still-valid authorizations, completed executions, and released controlled results. Each project shows its progress through the governed workflow (project, access request, Governance decision, Compute-to-Data execution, controlled result) and one next action linking to the relevant page; projects needing the researcher's attention come first. Governance approvals are listed with their conditions and validity, and one ending within 30 days or already expired raises a warning; an expired approval blocks the workflow until a new decision. Executions list the Hospital Nodes they ran on and their controlled result's disclosure check; the dashboard receives result release metadata only, never aggregate rows. The derivations are pure functions in `src/services/dashboard.ts`.
- **IMPLEMENTED (D1):** research project creation, HC-092 ([#84](https://github.com/Medmas07/Hackcure_hackathon/issues/84)), at `#new-project`. The researcher enters a title (10 to 150 characters, unique among their projects, ignoring case and spacing) and a scientific objective (30 to 1,000 characters). The project is created as a draft owned by the signed-in researcher and their organization, with no protocol, population, variables, hospitals, or access request; those are completed by HC-093 to HC-097, which the confirmation links to. A draft unlocks no Compute-to-Data page. The draft then appears on the home page and the dashboard. Identifiers continue after the fixture ones (`proj-003`), even in the empty scenario, so fixture executions are never attributed to a draft. Validation and creation are in `src/services/projectCreation.ts`.
- **IMPLEMENTED (D1):** research protocol and document upload, HC-093 ([#85](https://github.com/Medmas07/Hackcure_hackathon/issues/85)), at `#protocol`. The researcher picks one of their projects (the newest draft opens first) and deposits its research protocol (required before the access request) and, optionally, a data management plan and a patient information notice: PDF only, non-empty, 10 MB at most. A deposited document can be replaced or removed. Documents change only while the project is a draft without an access request; once submitted, they are shown locked, as the Governance / Ethics Authority reviews them. Fixture protocols are shown as received. Depositing a document requests no data access and unlocks no Compute-to-Data page. Validation, simulated upload, and the project update are in `src/services/projectDocuments.ts`.
- **PLANNED:** each page other than the home page, the dashboard, the new-project page, and the protocol page is a placeholder that names its ticket (HC-094 to HC-102). Compute-to-Data pages are shown as locked unless one of the researcher's projects holds a Governance approval that is still valid.
- **MOCKED:** `src/services/researchService.ts` reads the canonical fictional fixtures ([`demo-data/`](../../../demo-data/README.md), [ADR-0005](../../../docs/decisions/ADR-0005-canonical-demo-data.md)) in the browser with a simulated 400 ms delay. The signed-in identity is the fictional researcher Dr Aymen Rezgui (`usr-aymen`, `org-research-lab`); there is no authentication. Governance decisions are displayed only. A created project lives in the portal's session state only, with a simulated 400 ms delay; it is lost on reload. A deposited document's content is never read or sent: only its name, size, and media type are kept in session state, with simulated upload progress; no document-metadata contract exists yet. Nothing is executed, and no Research Service, Hospital Node, or SciAgents is contacted; no portal-facing Research Service contract exists yet (the [HC-180 execution contract](../../../contracts/api/research/research-node-execution.v1.yaml) is between the Research Service and Hospital Nodes, not the portal). Every page carries a `DemoBanner`.
- **Checked on 2026-10-10:** `npm run build`, `npm run lint`, and `npm test` (Vitest: fixture loading and Governance decision join, page order, Compute-to-Data locking by decision validity, demo scenarios, non-researcher identity refused; dashboard metrics, workflow steps and next action per state, approval expiry, result rows withheld; project draft validation, identifier numbering, draft creation, no Compute-to-Data unlock, invalid draft refused; document checklist, editing locked after submission, file validation, simulated progress and interruption, protocol recording, supporting-document replacement and removal) pass. HC-093: the served build was driven in headless Chrome: a new draft opened from its confirmation, a non-PDF file refused, upload progress, the protocol and an optional document deposited, removal, a submitted project locked, the interrupted-upload scenario and retry, the empty scenario, and a 360px-wide layout (no horizontal overflow, no console error). HC-092: the served build was driven in headless Chrome: empty and duplicate-title submission errors, the pending state, creation, the draft on the dashboard and home page, creation in the empty scenario (`proj-003`), and a 360px-wide layout (no horizontal overflow, no console error). HC-091: the dashboard was rendered from the served build in headless Chrome at 1366px and 360px (no horizontal overflow, no console error) and in the empty scenario. The built portal was served with `npm run preview` and rendered in headless Chrome: home page, an available placeholder, a locked Compute-to-Data page, the empty and error scenarios, and a 360px-wide layout.

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

Demo scenarios: append `?demo=vide` (no research project), `?demo=erreur` (simulated service failure), or `?demo=echec-depot` (the first document upload is interrupted) to the URL. Pages are addressed by hash, for example `#request-status` or `#workspace`.

## Responsibilities and owned concepts

- Researcher onboarding/subscription display, projects, protocols, requested cohorts/variables, and request status.
- Colab-like interface, Compute-to-Data job visualization, controlled results, and SciAgents access.

## Communication boundaries

The portal will use Research Service, Governance, job, and SciAgents Integration contracts. It never connects directly to hospital databases.

## Non-responsibilities

It does not grant ethics approval, export unrestricted raw clinical data, execute inside hospitals itself, or implement SciAgents.

## Expected contracts

PLANNED project/request, governance-status, research-job, controlled-result, and SciAgents request/response contracts.
