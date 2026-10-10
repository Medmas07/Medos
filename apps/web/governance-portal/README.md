# Governance Portal

## Purpose and status

- **IMPLEMENTED (D1):** Governance Portal shell (HC-070, [#71](https://github.com/Medmas07/Hackcure_hackathon/issues/71)), Governance dashboard (HC-071, [#72](https://github.com/Medmas07/Hackcure_hackathon/issues/72)), pending hospital approval list (HC-072, [#73](https://github.com/Medmas07/Hackcure_hackathon/issues/73)), hospital approval review (HC-073, [#74](https://github.com/Medmas07/Hackcure_hackathon/issues/74)), synchronization request list (HC-074, [#75](https://github.com/Medmas07/Hackcure_hackathon/issues/75)), approve/reject synchronization request (HC-076, [#77](https://github.com/Medmas07/Hackcure_hackathon/issues/77)), and research access request list (HC-077, [#78](https://github.com/Medmas07/Hackcure_hackathon/issues/78)) at initial depth D1. Built with React 19 + TypeScript + Vite SPA as decided in [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md) and styled with Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)).
- **Checked on 2026-10-10:** `npm test` (Vitest suite covering canonical demo-data loading, the pending hospital approval list, dashboard metrics calculation, federated nodes status, hash verification, state behavior, the hospital review rules, the synchronization list rules, the synchronization review rules, and the research access request list rules) all pass. Fixed dev port is `5174`.
- **Mocking strategy:** Consumes canonical fictional fixtures from `demo-data/` ([ADR-0005](../../../docs/decisions/ADR-0005-canonical-demo-data.md)). Simulated local ledger proofs (SHA-256) and advisory AI annotations are explicitly marked with `DemoBanner` and `DemoBadge`. No direct access to hospital clinical databases.

## Pending hospital approval list (HC-072)

IMPLEMENTED at D1, from the canonical fixtures. **Adhésions Hospitalières** opens on the applications awaiting review (`human_review` or `pending`), with queue counts (pending files, missing documents, advisory AI findings), a search on name, city, DMI system, or reference, a documents column showing missing pieces, and an empty state with a way back to all applications. The queue is read through `governanceService.getPendingHospitalApplications()`, so an application decided in the session (HC-073) leaves it until the demo is reset.

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

The request detail is a separate ticket (HC-075).

## Approve or reject a synchronization request (HC-076)

IMPLEMENTED at D1; the recorded decision is **SIMULATED**. A pending request (`sync-001` in the demo data) shows the Authority's decision form in its detail panel.

Deterministic checks, computed in `src/services/syncReview.ts` and unit-tested:

| Check | Conforme | Non conforme | À vérifier |
|---|---|---|---|
| Établissements agréés | requester and holder are two distinct organizations approved by the Authority | otherwise | — |
| Base d’autorisation | the patient grant exists, is active, not revoked or expired, is for this patient, and covers the requested scope | no basis, or any grant problem | signed consent form or emergency override: not verifiable in the portal |
| Durée | at least one day is possible | the patient grant has lapsed | — |

- **The authorization never outlasts the patient's grant.** The approved duration defaults to, and may not exceed, the requested duration capped by the grant's expiry. In the demo, 30 days are requested, `grant-a-drx` ends on 2026-10-24, and so at most 13 days can be approved; a shortened duration is added to the decision's conditions.
- Approval is disabled while any check fails; a motivated refusal is always possible. A check the portal cannot verify must be confirmed by the reviewer.
- A rationale of at least 20 characters is required; conditions are optional.
- Only a governance reviewer outside both the requesting and the holding organizations may decide, and a decided request cannot be decided again.
- After a confirmation step and a short simulated delay, the decision (temporary, with its `validUntil`) and a `decision_recorded` audit event (references only) are kept in the same local store as HC-073. The list then shows the request as authorized until its end date, the sidebar badge and dashboard counts drop, and the audit views list the event as not anchored. **Réinitialiser la démo** or a reload returns to the fixtures.

Not done at D1: nothing is sent to the Governance Node (its synchronization API, HC-132, is PLANNED) or to any Hospital Node. Federation queries and the Hospital Nodes' MOCKED authorization still read only the canonical fixtures, so a simulated approval authorizes no real exchange. No ledger proof is created, and the reviewer is the fictional demo reviewer, not an authenticated user.

## Research access request list (HC-077)

IMPLEMENTED at D1, read-only, from the canonical fixtures. **Recherche Biomédicale** lists multicentric research access requests evaluated under the strict **Compute-to-Data** paradigm:

- request id (`rar-001`, `rar-002`) and linked project id & title (`proj-001`, `proj-002`);
- principal investigator (`Dr Aymen Ben Salah`) and affiliated research organization (`Laboratoire de Recherche Biomédicale`);
- participating target hospital nodes (`HU Bab Ennour`, `HR Oued Zitoun`, `Cabinet Bouzid`);
- execution mode explicitly labelled `Compute-to-Data`, emphasizing the core architecture invariant: research algorithms run inside hospital node sandboxes and raw patient data never leaves node boundaries;
- status as of today: `En examen` (under_review), `Autorisée` (active, with expiration date), `Expirée` (expired authorization), or `Rejetée` (rejected);
- prioritized ordering: requests awaiting review first (`under_review`), followed by active, expired, and rejected, newest first within each;
- interactive status filters with counts and empty state fallback, alongside a detail preview panel with study population, requested variables, protocol document, and decision state.

The request detail review (HC-078) and decision workflow (HC-079) are separate tickets.

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
