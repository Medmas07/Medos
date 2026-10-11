# ADR-0001: Web frontend technology for the three web portals

## Status

Accepted — 2026-10-10, through review of HC-001 ([#24](https://github.com/Medmas07/Hackcure_hackathon/issues/24)).

## Context

The repository plans three web products: the [Hospital Portal](../../apps/web/landing/README.md), the [Governance Portal](../../apps/web/governance-portal/README.md), and the [Research Portal](../../apps/web/research-portal/README.md). Before this decision, all three were PLANNED with no frontend framework or UI code, and the web framework/build tool was listed in [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md). HC-004 (visual design system) and the portal shells HC-050, HC-070, and HC-090 are blocked on this choice.

Constraints that drive the choice:

- **One technology for all three portals**, so the HC-004 design system and contributor knowledge carry across portals.
- **Two-day hackathon:** fast setup, fast dev feedback, a widely known stack, and no dependence on paid services.
- **Demo-first:** portals initially render fictional HC-005 data and deterministic mocks, later explicit mock APIs.
- **Portals are clients, not backends.** [Architecture](../architecture.md) requires portals to communicate through explicit contracts with Governance Node, onboarding, Research Service, and SciAgents Integration APIs. A portal must never access persistence directly, and the repository forbids a generic backend location.
- **No server-side rendering requirement:** the portals are authenticated work tools (review queues, forms, job status) and SEO does not matter.
- **Hosting is OPEN.** The product vision lists Vercel, Render, or controlled machine hosting as candidates only, so output should be portable static files.
- The Research Portal's Colab-like workspace will need rich client-side interactivity. Notebook execution remains a Research Service / Compute-to-Data concern, not a browser concern.

## Decision

All three web portals use:

| Concern | Choice |
|---|---|
| UI library | React (19.x at time of decision) |
| Language | TypeScript (strict mode, as scaffolded) |
| Build tool / dev server | Vite (8.x at time of decision) via the `react-ts` template of `create-vite` |
| Application model | Client-side single-page application; static build output (`dist/`) |
| Package manager | npm (bundled with Node.js) |
| Runtime for tooling | Node.js LTS, minimum `^20.19.0 \|\| >=22.12.0` (Vite engine requirement) |
| Lint | `oxlint`, as provided by the current template |

Each portal is an independent Vite project in its existing directory (`apps/web/landing/`, `apps/web/governance-portal/`, `apps/web/research-portal/`). Portals do not import from each other.

### Commands

Scaffold (run once per portal by its shell ticket: HC-050, HC-070, HC-090; not by HC-001). `create-vite` refuses a non-empty directory, and each portal directory already contains a README.md that must be kept. Scaffold into a temporary folder and copy everything except the template README:

```bash
# from the repository root, in a POSIX shell (Git Bash on Windows); <portal> is e.g. landing
npm create vite@9.2.1 .scaffold/<portal> -- --template react-ts --no-interactive
rm .scaffold/<portal>/README.md
cp -r .scaffold/<portal>/. apps/web/<portal>/
rm -rf .scaffold
cd apps/web/<portal> && npm install
```

Pinning `create-vite@9.2.1` gives all three portals the same template. A later ADR or ticket may raise the pin.

Daily development and validation, from inside `apps/web/<portal>/`:

| Purpose | Command |
|---|---|
| Install dependencies | `npm install` (use `npm ci` in CI once a lockfile exists) |
| Dev server with hot reload | `npm run dev` |
| Type-check and production build | `npm run build` (`tsc -b && vite build`, output in `dist/`) |
| Lint | `npm run lint` |
| Local production preview | `npm run preview` |

Suggested fixed dev ports, set in each `vite.config.ts` with `server.port`, so all three portals can run at once: Hospital Portal `5173`, Governance Portal `5174`, Research Portal `5175`.

### Evidence

On 2026-10-10, a throwaway project was scaffolded outside the repository with `create-vite@9.2.1 --template react-ts` on Node.js 24.13.0 / npm 11.6.2. `npm install`, `npm run build`, `npm run lint`, and `npm run preview` (the page was served) all succeeded. The temporary-folder scaffold flow above was also checked against a directory with an existing README.md: the README was kept and the result built. This validates the toolchain commands only. No portal was implemented.

## Alternatives considered

- **Next.js (React meta-framework):** strong React ecosystem and a good fit for Vercel. Rejected for now because its server runtime (route handlers, server actions, server components) invites portal-local backend logic. That would blur the contract boundary to the Governance Node and company services, and it would be an unplanned backend. It also ties hosting toward a Node server or Vercel while hosting is still OPEN, and it adds concepts the team does not need for a two-day demo.
- **Angular:** complete and opinionated, but heavier to set up and learn under hackathon time pressure. Its smaller component ecosystem would slow the HC-004 design system.
- **Vue + Vite / SvelteKit:** both are productive and lightweight. React was preferred for the larger ecosystem of ready UI, table, form, and code-editor components, which the Research Portal's notebook-like workspace and the review tables need, and for broader team familiarity. SvelteKit also brings an optional server layer, with the same concern as Next.js.
- **Server-rendered templates from a backend runtime:** this would couple the portals to a backend stack that HC-003 has not chosen yet and would weaken the client/contract separation.

## Consequences

### Positive

- One stack and one set of commands for all three portals, so contributors can move between them.
- Static build output keeps hosting portable across the candidates the product vision lists.
- The SPA model enforces the boundary: a portal can only reach data through HTTP APIs/contracts and has no server-side place to put persistence access.
- Unblocks HC-004 and the portal shells HC-050, HC-070, and HC-090.

### Negative

- Every portal needs a reachable API (or deterministic local mock data) for each screen, with no server-side shortcut. This is intended, but it means mock APIs are needed early (Milestone 2).
- A client-only SPA exposes its JavaScript bundle. No secrets or real data may ever be embedded in portal code or `VITE_*` variables, because every `VITE_*` value ends up in the browser bundle.
- Three independent projects means three dependency trees until a sharing approach is chosen for the design system.
- React, Vite, TypeScript, and template defaults change quickly. The versions above are a snapshot; each portal pins its own versions through its lockfile.

## Follow-up

- HC-050, HC-070, HC-090: scaffold each portal with the commands above, keeping the existing README, and set the fixed dev port.
- HC-004: decide styling approach and **where reusable design-system code lives**. Repository rules reserve `apps/` for named products and forbid generic `shared/` folders, so this location is OPEN (see [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md)).
- Not decided here and left to the tickets that first need them: client-side routing, data-fetching library, form library, component/unit test runner (Vitest is the natural candidate with Vite), and E2E tooling.
- After the first portal exists: replace the placeholder lint/CI workflows with real `npm ci`, `npm run lint`, and `npm run build` steps.
- Frontend hosting stays OPEN and needs its own ADR.
