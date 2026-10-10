# Hospital Portal

## Purpose and status

Company-managed web product for hospital onboarding. React 19 + TypeScript + Vite SPA per [ADR-0001](../../../docs/decisions/ADR-0001-web-frontend-technology.md), styled with Tailwind CSS v4 and the shared [design system](../../../design-system/README.md) ([ADR-0002](../../../docs/decisions/ADR-0002-web-design-system.md)).

- **IMPLEMENTED (D1):** the portal shell, HC-050 ([#57](https://github.com/Medmas07/Hackcure_hackathon/issues/57)). It has a sidebar with the onboarding workflow (registration, profile, documents, agreements, technical and DMI/HIS questionnaires, automated review, human review, Governance decision) and the Hospital Node pages (configuration, download, installation guide, status). The onboarding dashboard shows the application status, progress, next step, step timeline, and notifications. It also shows loading, empty, and error states.
- **IMPLEMENTED (D1), MOCKED submission:** hospital registration flow, HC-051 ([#58](https://github.com/Medmas07/Hackcure_hackathon/issues/58)), at `#registration`. A three-step form (establishment, responsible manager, review and send) with per-step validation and two required confirmations, one of them stating that registration is not approval. `src/services/registrationService.ts` simulates submission with a delay. It re-validates the form, rejects an establishment name already in the fictional registry, and returns a deterministic reference (`REG-<date>-<short name>`). The result is kept in memory only, as a local `draft` application that updates the dashboard; reloading the page discards it. No account is created and nothing leaves the browser. A "fill with the fictional example" button enters the canonical Cap Azur data. When an application already exists (the default fixture), the page shows its registration summary.
- **IMPLEMENTED (D1), MOCKED save:** organization profile, HC-052 ([#59](https://github.com/Medmas07/Hackcure_hackathon/issues/59)), at `#profile`. It holds the administrative information sent with the application: legal identity, address and contact, legal representative, data protection officer, and an optional security contact. Without a registration, the page shows an empty state linking to registration. For a local `draft` application, the form is prefilled from the registration and can be saved and edited again. `src/services/profileService.ts` validates the profile (required fields, formats; the security contact must be complete if given) and simulates the save; the result is kept in memory only. Once the application is submitted for review (the default fixture), the profile is read-only. The canonical Cap Azur profile lives in `demo-data/governance.json`; its missing security contact is shown as a non-blocking recommendation.
- **PLANNED:** the other workflow pages are placeholders that name their ticket (HC-053 to HC-063). Node pages are shown as locked until a Governance approval exists.
- **MOCKED:** `src/services/onboardingService.ts` reads the canonical fictional fixtures ([`demo-data/`](../../../demo-data/README.md), [ADR-0005](../../../docs/decisions/ADR-0005-canonical-demo-data.md)) in the browser with a simulated 400 ms delay. The signed-in identity is the fictional manager of Centre Hospitalier Cap Azur (`usr-mehdi`, application `app-hospital-c`); there is no authentication. Step states are derived from that application. No onboarding API or contract exists yet. Every page carries a `DemoBanner`.
- **Checked on 2026-10-10:** `npm run build`, `npm run lint`, and `npm test` (Vitest: fixture loading, step derivation, locked Node pages before approval, demo scenarios, registration validation, duplicate rejection, simulated failure, local draft application, profile validation, locked profile under review, profile save) pass. The profile was driven end to end in headless Chromium (locked fixture profile, empty state, prefill after registration, validation errors, failed then retried save, edit and cancel, dashboard progress, 360px layout), as was the registration flow against the served build: validation errors, a failed then retried submission, duplicate rejection, a successful registration, the updated dashboard, and the 360px layout, with no page errors. The built portal was served with `npm run preview` and rendered in headless Chromium: dashboard, a placeholder page, a locked Node page, the empty and error scenarios, and a 360px-wide layout.

## Commands

From inside `apps/web/hospital-portal/` (run `npm install` in [`design-system/`](../../../design-system/README.md) once as well):

| Purpose | Command |
|---|---|
| Install dependencies | `npm install` |
| Dev server on <http://localhost:5173> | `npm run dev` |
| Type-check and production build | `npm run build` |
| Lint | `npm run lint` |
| Unit tests | `npm test` |
| Preview the build | `npm run preview` |

Demo scenarios: append `?demo=vide` (no application submitted, so the registration form is shown), `?demo=echec-inscription` (as `vide`, and the first registration submission fails), `?demo=echec-profil` (as `vide`; register first, then the first profile save fails), or `?demo=erreur` (simulated service failure) to the URL. Each simulated failure happens once per page load. Pages are addressed by hash, for example `#documents` or `#node-download`.

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
