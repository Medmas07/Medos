# ADR-0007: MedOS landing page as the hospital entry point, with a guided onboarding journey

## Status

Accepted — 2026-10-11, decided by the product owner (AhmedChabbouh) on branch `feat/front`; subject to pull-request review.

## Context

The Hospital Portal (`apps/web/hospital-portal/`, HC-050 to HC-063) was built as a **back-office dashboard**. Opening it showed an `AppShell` with a sidebar listing the 13 onboarding and Hospital Node pages and the onboarding dashboard (`#overview`). The fictional Cap Azur manager was already signed in, and the application was already under human review.

That reading of the product vision ([§4 Hospital onboarding](../product/FEDERATED_HEALTHCARE_ECOSYSTEM.md#4-hospital-onboarding), [§7 Installation and distribution](../product/FEDERATED_HEALTHCARE_ECOSYSTEM.md#7-hospital-node-installation-and-distribution)) was a **misconception about how a hospital arrives**:

- the product had no public face. Nothing presented the ecosystem, which is named **MedOS**, before a manager was dropped into an internal tool;
- a hospital's goal is to **obtain its Hospital Node instance**. The portal showed onboarding as 13 independent pages to browse in any order, not as a path that ends with the download;
- starting from a dossier already under review hid the forms, which are the actual onboarding work;
- the download sat on the same level as every other page. Nothing said that the configuration guide comes first, then the download, then the installation.

The intended experience is: a visitor lands on a MedOS presentation page and clicks **"Télécharger l'instance pour hôpitaux"**. They then fill the existing onboarding **forms one after the other**, and after the Governance decision they see the **configuration guide and then the download button**.

## Decision

- **Rename** `apps/web/hospital-portal/` to `apps/web/landing/`, with package name `landing`. The app now holds the MedOS landing page and the hospital onboarding product. The decision changes no other boundary.
- **The landing page is the default route** (no hash). It is adapted from the Medora design concept (Three.js scroll story, ecosystem, trust, and hospitals sections) to the design-system tokens and to the product vision. The 3D scene is lazy-loaded; phones and browsers without WebGL get a CSS fallback.
- **The guided journey** (`#adhesion/<step>`) is started by "Télécharger l'instance pour hôpitaux". It runs in this order:
  1. the forms: registration, profile, documents, agreements, technical questionnaire, and DMI/HIS questionnaire;
  2. submission and validation: automated checks with submission, human review, and the Governance decision;
  3. the hospital instance: the **configuration guide**, then **download of the instance**, then the installation guide and the Node status.

  The journey starts from an empty dossier and has a progress sidebar and previous/next navigation.
- **Pages are reused, not rewritten.** The journey renders the existing views through `src/views/StepView.tsx`, and the same MOCKED services through `src/useOnboardingSnapshot.ts`. The HC-051 to HC-063 behaviour and tests are unchanged.
- **The dashboard portal is removed** (amended 2026-10-11, same review). The sidebar "Espace établissement" (`#overview`) duplicated the journey and kept the old dashboard-first model alive. Its entry points become a simple **"Se connecter"** button leading to a sign-in page (`#connexion`). Authentication is not implemented there: nothing is checked, stored, or sent, and submitting does nothing for now. The clinician alerts view (HC-203), reachable only from that dashboard, has no entry point until its owner relocates it.
- **Governance invariant unchanged:** configuration and download stay locked until the Governance / Ethics Authority approves. The journey never approves anything. While a dossier waits for a decision, a labelled link reloads the journey on the existing `?demo=decision-approuvee` scenario (the fictional Cap Azur dossier with a simulated approval), so the end of the path can be demonstrated.

Hash routing is defined in `apps/web/landing/src/route.ts`. Details and validation are in the [component README](../../apps/web/landing/README.md).

## Alternatives considered

- **Keep the dashboard as the entry point and add a "start" button:** small change, but the product still has no public face and the path to the download stays implicit.
- **A separate landing app (`apps/web/landing/` next to `hospital-portal/`):** clean split, but it duplicates the onboarding views or makes one portal import from another, which [ADR-0001](ADR-0001-web-frontend-technology.md) forbids.
- **Rewrite onboarding as a new wizard:** would lose the validated HC-051 to HC-063 behaviour and tests for no product gain.
- **CSS-only landing without Three.js:** lighter, but loses the scroll story that carries the message (records gathered locally, every exchange authorized by Governance).

## Consequences

### Positive

- One clear path from discovery to the downloaded Hospital Node, matching the vision's onboarding workflow.
- The forms are visible from an empty dossier, which demonstrates the real onboarding work.
- One way through onboarding: the journey reaches every onboarding and Node page, with no parallel dashboard to keep in sync.

### Negative

- New runtime dependencies in this app: `three`, `@react-three/fiber`, `gsap`, `lenis`, `lucide-react`. The lazy 3D chunk is about 248 kB gzipped.
- Paths changed: running dev servers, scripts, and links that point at `apps/web/hospital-portal/` must use `apps/web/landing/`. Documentation links were updated.
- The approval demo link replaces the visitor's local entries with the Cap Azur fixture. That is acceptable for a demo, but it is not a continuous journey on the visitor's own data. A real continuation needs the PLANNED onboarding and approval-status contracts.

## Follow-up

- Replace the demo approval link with the real approval status once the Governance decision contract exists.
- Connect the "Se connecter" page to real authentication once it is decided (OPEN); until then it is a labelled placeholder.
- Give the clinician alerts view (HC-203) an entry point in the product that owns clinician alerts, or remove it.
