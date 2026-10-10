# Governance Portal

## Purpose and status

- **IMPLEMENTED (D1):** Governance Portal shell (HC-070, [#71](https://github.com/Medmas07/Hackcure_hackathon/issues/71)), Governance dashboard (HC-071, [#72](https://github.com/Medmas07/Hackcure_hackathon/issues/72)), pending hospital approval list (HC-072, [#73](https://github.com/Medmas07/Hackcure_hackathon/issues/73)), hospital approval review (HC-073, [#74](https://github.com/Medmas07/Hackcure_hackathon/issues/74)), synchronization request list (HC-074, [#75](https://github.com/Medmas07/Hackcure_hackathon/issues/75)), synchronization request detail (HC-075, [#76](https://github.com/Medmas07/Hackcure_hackathon/issues/76)), approve/reject synchronization request (HC-076, [#77](https://github.com/Medmas07/Hackcure_hackathon/issues/77)), research access request list (HC-077, [#78](https://github.com/Medmas07/Hackcure_hackathon/issues/78)), research access request review (HC-078, [#79](https://github.com/Medmas07/Hackcure_hackathon/issues/79)), governance audit timeline (HC-079, [#80](https://github.com/Medmas07/Hackcure_hackathon/issues/80)), blockchain proof explorer (HC-080, [#81](https://github.com/Medmas07/Hackcure_hackathon/issues/81)), and notification UI fixtures (HC-200, [#158](https://github.com/Medmas07/Hackcure_hackathon/issues/158)) at initial depth D1. Built with React 19 + TypeScript + Vite SPA as decided in [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md) and styled with Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)).
- **Checked on 2026-10-10:** `npm run build`, `npm run lint`, and `npm test` (Vitest suite covering canonical demo-data loading, the pending hospital approval list, dashboard metrics calculation, federated nodes status, hash verification, state behavior, the hospital review rules, the synchronization list rules, synchronization request detail verification, the synchronization review rules, the research access request list rules, the research review rules, the audit timeline rules, the proof verification rules, and the notification service rules) all pass. Fixed dev port is `5174`.
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

Not done at D1: the decision is not sent to the Governance Node (its hospital approval API, HC-131, exists, but the portal does not call it yet) or persisted; no ledger proof is created; the reviewer is the fictional demo reviewer (`usr-olfa`), not an authenticated user; Hospital Node configuration and package generation after approval are out of scope.

## Synchronization request list (HC-074)

IMPLEMENTED at D1, read-only, from the canonical fixtures. **Synchronisations Soins** lists every inter-hospital synchronization request with what the reviewer needs to triage it (demo scenario step 20):

- request id, requesting organization → organization holding the data, the patient's **pseudonymous federated id** (never the name), and the submission date;
- purpose, requested scope in readable labels (Consultations, Médicaments, Analyses biologiques), requested duration, and consent basis;
- status **as of today**: `En attente`, `Autorisée` (with its end date), `Expirée` (an approved request whose decision has lapsed no longer authorizes any exchange), or `Rejetée`.

Requests are ordered pending first, then authorized, expired, and rejected, newest first within each. Filters by status show their counts, and a filter with no result shows an empty state with a way back to all requests. The rules live in `src/services/syncRequestList.ts` and are unit-tested; statuses use the browser clock, evaluated when the page opens. In the demo data, `sync-002` (approved until 2026-03-12) therefore shows as expired, and the detail panel says so too.

## Synchronization request detail (HC-075)

IMPLEMENTED at initial depth D1. In **Synchronisations Inter-Hospitalières**, selecting any synchronization request displays its complete detail dossier (`SyncRequestDetail`):

1. **Source & target hospitals:** Identifies requester and custodian hospitals (`reqOrg`, `tgtOrg`), city, federated node status (`online`/`degraded`), DMI adapter connection state, and local patient record identifiers (IPP/MRN) mapped across establishments. Invariant emphasized: target hospital retains exclusive sovereignty over its source clinical data; no direct SQL or centralized extraction.
2. **Clinical purpose & justification:** Displays declared clinical purpose, submission date, and ethical review classification (continuity of care vs unauthorized research request).
3. **Patient identity & data scope:** Resolved federated patient identity (`FED-PAT-0001`, demographics) and clinical categories in scope (`medications`, `labReports`, `encounters`) with descriptive labels and minimization principle indicator.
4. **Duration & timeframe:** Requested duration in consecutive days, timestamp, and proportionality assessment based on care episode.
5. **Consent state & authorization basis:**
   - Active patient grant (`patient_grant`): Linked to `access.json` (`grant-a-drx`), showing attending practitioner grantee (`Dr Youssef Gharbi`), expiration date, and scope alignment check.
   - Signed consent form (`signed_consent_form`): Physical paper consent documented at emergency intake.
   - Missing consent (`none`): Flagged with violation alert, demonstrating federation invariant prohibiting unconsented data transfer.
6. **Governance decision & cryptographic proof:** Displays outcome, rationale, conditions, reviewer (`usr-olfa`), and anchored SHA-256 fingerprint for decided requests, or instruction notice for pending requests.

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

Not done at D1: nothing is sent to the Governance Node (its synchronization request API, HC-132, exists, but the portal does not call it yet) or to any Hospital Node. Federation queries and the Hospital Nodes' MOCKED authorization still read only the canonical fixtures, so a simulated approval authorizes no real exchange. No ledger proof is created, and the reviewer is the fictional demo reviewer, not an authenticated user.

## Research access request list (HC-077)

IMPLEMENTED at D1, read-only, from the canonical fixtures. **Recherche Biomédicale** lists multicentric research access requests evaluated under the strict **Compute-to-Data** paradigm:

- request id (`rar-001`, `rar-002`) and linked project id & title (`proj-001`, `proj-002`);
- principal investigator (`Dr Aymen Rezgui`) and affiliated research organization (`Labo Cardiométabolique`);
- participating target hospital nodes (`HU Bab Ennour`, `HR Oued Zitoun`, `Cabinet Bouzid`);
- execution mode explicitly labelled `Compute-to-Data`, emphasizing the core architecture invariant: research algorithms run inside hospital node sandboxes and raw patient data never leaves node boundaries;
- status as of today: `En examen` (under_review), `Autorisée` (active, with expiration date), `Expirée` (expired authorization), or `Rejetée` (rejected);
- prioritized ordering: requests awaiting review first (`under_review`), followed by active, expired, and rejected, newest first within each;
- interactive status filters with counts and empty state fallback, alongside a detail preview panel with study population, requested variables, protocol document, and decision state.

Reviewing a request and recording the Authority's decision are described in the next section (HC-078).

## Research access request review (HC-078)

IMPLEMENTED at D1; the recorded decision is **SIMULATED**. Under **Accès Recherche**, a request's detail now shows the project the Authority is judging (objective, population, requested variables, participating organizations, protocol). A request under review (`rar-002` in the demo data) shows the ethics committee's decision form.

Deterministic checks (`src/services/researchReview.ts`, unit-tested): the request matches its project; a protocol is attached; a population and at least one variable are defined; at least one participating organization is approved by the Authority with a Hospital Node (others are excluded and cannot be authorized). Approval is disabled while a check fails; a motivated rejection is always possible.

An approval states exactly what it authorizes, in the shape the [research execution contract](../../../contracts/api/research/research-node-execution.v1.yaml) expects of an authorization:

- **Organizations and variables** default to the whole eligible request and can only be narrowed. A participating node whose DMI is disconnected is flagged.
- **Validity:** 1 to 12 months (default 12), and **minimum cell size:** at least 10 (default 10). Both limits are D1 demo policy taken from the canonical approved request `dec-rar-001`, not a decided policy.
- Compute-to-Data execution and no individual-level output are always imposed. The decision stores the authorized organizations, variables, and cell size as `researchAuthorization` and states them as conditions; optional extra conditions follow.
- Only a governance reviewer outside the research organization and the participating organizations, and not the investigator, may decide; a decided request cannot be decided again.

After a confirmation step and a short simulated delay, the decision and its `decision_recorded` audit event (references only) join the local store used by HC-073 and HC-076: the list status, sidebar badge, dashboard counts, and audit views follow, and **Réinitialiser la démo** or a reload returns to the fixtures. A rejection is shown in red; previously every decision was shown as approved.

Not done at D1: nothing is sent to the Governance Node (its research request API, HC-133, exists, but the portal does not call it yet), the Research Service, or any Hospital Node, so a simulated approval authorizes no execution. No ledger proof is created, and the reviewer is the fictional demo reviewer, not an authenticated user. The request list itself is HC-077.

## Governance audit timeline (HC-079)

IMPLEMENTED at D1, from the canonical fixtures and the session's simulated decisions. **Piste d’Audit & Registre** shows the Governance Node's audit events as a timeline, newest first, under the ledger proofs:

- Each event says what happened in plain language: `Décision : synchronisation rejetée`, `Demande d’adhésion déposée`, `Demande de synchronisation reçue`. For a decision it resolves the request it was about (`sync-003`) and its outcome, coloured green for approved and red for rejected.
- The actor (or "reçue automatiquement"), the event id, and the organizations involved.
- Whether a ledger proof anchors the event, with **Vérifier** opening it in the proof verifier, or `Non ancré`.
- Filters by domain (adhésions, synchronisations, recherche) with counts, and by organization; a combination with no event shows an empty state with a way back.
- A decision recorded in the session (HC-073, HC-076, HC-078) appears at once at the top, in the demo colour and labelled `Simulé — non persisté`.

The rules live in `src/services/auditTimeline.ts` and are unit-tested, including a check that no event carries patient identity. Events hold references only. This is the Governance Node's own trail: each Hospital Node keeps its own audit of data access (HC-116), which is not centralized here. An event whose decision cannot be resolved is still listed, as `Décision enregistrée`.

The dashboard's "Dernières Actions" card now uses the same newest-first order; it previously showed the six oldest events.

Not done at D1: events come from fixtures and local state, not from the Governance Node audit API (HC-134 is PLANNED); simulated decisions get no ledger proof.

## Blockchain proof explorer (HC-080) — MOCKED BLOCKCHAIN

IMPLEMENTED at D1 against a **MOCKED BLOCKCHAIN**: the "ledger" is the simulated proof list in `demo-data/governance.json`. There is no chain, network, consensus, or real anchoring; the explorer, its badge, and its banner say so. The `AuditLedgerPort` and a simulated or real ledger are PLANNED (HC-190 to HC-194).

**Piste d’Audit & Registre** lists each proof with its event type in plain language (`Décision : accès recherche approuvée`), proof and event ids, hash, organizations, anchoring time, and its verification state. That state is **recomputed in the browser**, not read from the fixture's own `verificationStatus` claim:

- **Vérifiée:** the SHA-256 of the canonical payload matches the recorded hash, the payload names the proof's audit event and that event exists, and the payload holds only the allowed minimized fields (`eventId`, `decisionId`, `outcome`, `decidedAt`, `organizationIds`, `version`, the same set as `check_fixtures.py`).
- **Altérée:** the recomputed hash differs.
- **Incohérente:** the hash matches, but the proof points to another or a missing event, or anchors a forbidden field such as a diagnosis.

Selecting a proof shows the recorded and recomputed hashes, each check, the anchored payload, a warning if the fixture's claimed status disagrees with the recomputation, and a link that opens it in the interactive verifier. Verification is asynchronous (Web Crypto), with a loading state, and an error state when Web Crypto is unavailable (outside HTTPS or localhost).

The rules live in `src/services/proofExplorer.ts` and are unit-tested. Its `canonicalJson` reproduces Python's `json.dumps(sort_keys=True, separators=(',', ':'))` byte for byte, sorting keys at every depth and escaping non-ASCII. The previous shared implementation dropped the keys of nested objects, so a change inside a nested object went undetected; the verifier and `governanceService` now use the corrected one.

Simulated decisions recorded in the session (HC-073, HC-076, HC-078) get no proof; the timeline shows them as not anchored.

## Notification UI fixtures (HC-200)

IMPLEMENTED at D1, from the canonical fixtures (`demo-data/notifications.json`). **Notifications** displays the governance reviewer's notification center:

- notification types mapped to French labels, visual tones, and icons: `Accès accordé`, `Nouveau dossier`, `Délégation`, `Suivi de demande`, `Alerte clinique`, `Revue demandée`, `Exécution terminée`;
- ordering: unread notifications first, then newest first within each group;
- type summary cards with counts, and interactive filter tabs with empty state fallback;
- Timeline rendering using the design-system `Timeline` component, with tone-colored markers and pulsing indicators for unread items;
- detail table with status, type badge, title, body, related reference, and date;
- **mark-as-read** (individual and bulk) is **SIMULATED** (in-memory, session-only); `Réinitialiser la démo` or a page reload returns to fixture state;
- sidebar navigation badge showing unread count with danger tone, updated reactively.

The rules live in `src/services/notificationService.ts` and are unit-tested (19 tests covering data loading, type mapping, ordering, filtering, counts, mark-as-read simulation, session store subscription, relative time formatting, and data integrity).

Not done at D1: no broker, WebSocket, or real notification delivery service is connected. Notifications come from static fixtures, not from a Notification Service API (HC-201 to HC-204 are PLANNED upgrades). The banner says so explicitly.

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
