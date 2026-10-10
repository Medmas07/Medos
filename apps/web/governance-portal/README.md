# Governance Portal

## Purpose and status

- **IMPLEMENTED (D1):** Governance Portal shell (HC-070, [#71](https://github.com/Medmas07/Hackcure_hackathon/issues/71)), Governance dashboard (HC-071, [#72](https://github.com/Medmas07/Hackcure_hackathon/issues/72)), hospital approval review (HC-073, [#74](https://github.com/Medmas07/Hackcure_hackathon/issues/74)), and synchronization request list (HC-074, [#75](https://github.com/Medmas07/Hackcure_hackathon/issues/75)) at initial depth D1. Built with React 19 + TypeScript + Vite SPA as decided in [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md) and styled with Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)).
- **Checked on 2026-10-10:** `npm run build`, `npm run lint`, and `npm test` (Vitest suite covering canonical demo-data loading, dashboard metrics calculation, federated nodes status, hash verification, state behavior, the hospital review rules, and the synchronization list rules) all pass. The review flow and the synchronization list were also driven in headless Chrome. Fixed dev port is `5174`.
- **Mocking strategy:** Consumes canonical fictional fixtures from `demo-data/` ([ADR-0005](../../../docs/decisions/ADR-0005-canonical-demo-data.md)). Simulated local ledger proofs (SHA-256) and advisory AI annotations are explicitly marked with `DemoBanner` and `DemoBadge`. No direct access to hospital clinical databases.

## Hospital approval review (HC-073)

IMPLEMENTED at D1; the recorded decision is **SIMULATED**. Under **Adhésions Hospitalières**, an application awaiting human review (Hospital C, `app-hospital-c`, in the demo data) shows a review form under its file:

1. **Points to examine:** missing documents, unaccepted agreements, the deterministic completeness findings, and the AI findings, which are labelled advisory and non-binding. The reviewer must tick that each point was examined.
2. **Decision:** approve or reject, with a rationale of at least 20 characters. Approving an incomplete application requires at least one condition, one per line; a rejection carries none.
3. **Confirmation:** a summary to confirm or edit, then a short simulated delay.

The rules live in `src/services/hospitalReview.ts` and are unit-tested. Only a person with the `governance_reviewer` role from outside the applicant organization may decide, so an applicant never approves its own request, and an application already decided cannot be decided again.

The decision and its `decision_recorded` audit event (references only) are kept in `src/services/reviewStore.ts`, local in-memory state that `governanceService` merges with the fixtures. The application then shows as approved or rejected everywhere in the portal: its file, the filters, the sidebar badge, the dashboard counts, and the audit views, where the event is listed as not anchored. **Réinitialiser la démo** returns to the fixtures, and so does a reload.

Not done at D1: the decision is not sent to the Governance Node (its decision API, HC-131, is PLANNED) or persisted; no ledger proof is created; the reviewer is the fictional demo reviewer (`usr-olfa`), not an authenticated user; Hospital Node configuration and package generation after approval are out of scope.

## Synchronization request list (HC-074)

IMPLEMENTED at D1, read-only, from the canonical fixtures. **Synchronisations Soins** lists every inter-hospital synchronization request with what the reviewer needs to triage it (demo scenario step 20):

- request id, requesting organization → organization holding the data, the patient's **pseudonymous federated id** (never the name), and the submission date;
- purpose, requested scope in readable labels (Consultations, Médicaments, Analyses biologiques), requested duration, and consent basis;
- status **as of today**: `En attente`, `Autorisée` (with its end date), `Expirée` (an approved request whose decision has lapsed no longer authorizes any exchange), or `Rejetée`.

Requests are ordered pending first, then authorized, expired, and rejected, newest first within each. Filters by status show their counts, and a filter with no result shows an empty state with a way back to all requests. The rules live in `src/services/syncRequestList.ts` and are unit-tested; statuses use the browser clock, evaluated when the page opens. In the demo data, `sync-002` (approved until 2026-03-12) therefore shows as expired, and the detail panel says so too.

The request detail (HC-075) and approving or rejecting a request (HC-076) are separate tickets.

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
