# ADR-0002: Location and styling of the web design system

## Status

Accepted — 2026-10-10, chosen by the HC-004 assignee during HC-004 ([#27](https://github.com/Medmas07/Hackcure_hackathon/issues/27)); subject to pull-request review.

## Context

[ADR-0001](ADR-0001-web-frontend-technology.md) selected React + TypeScript + Vite for the three web portals and left two questions to HC-004: the styling approach, and **where reusable design-system code lives**. The location was OPEN because repository rules reserve `apps/` for named products and forbid generic `shared/` folders and speculative packages.

Constraints:

- The three portals are independent Vite projects and must not import from each other.
- HC-004 blocks the three portal shells (HC-050, HC-070, HC-090) and the two mobile shells (HC-010, HC-030), but the mobile framework (HC-002) is still OPEN.
- MOCKED and fictional content must be visibly labelled across every surface.
- Two-day hackathon: minimal tooling, fast iteration, no paid services.

## Decision

- **Location:** a named top-level boundary, `design-system/`, containing one private npm package, `@hackcure/design-system`. It is a design system for the web portals, not a generic shared folder: it holds only design tokens, base typography, presentational React components, and a showcase page. Domain logic, data access, API clients, and fixtures are excluded.
- **Consumption:** each portal adds a local `file:` dependency (`npm install ../../../design-system`). Portals compile the package's TypeScript source directly; nothing is pre-built or published. Each portal's `vite.config.ts` must set `resolve.dedupe: ['react', 'react-dom']`. No root-level npm workspace is introduced.
- **Styling:** Tailwind CSS v4 (4.3.x at time of decision) through `@tailwindcss/vite`. Tokens are declared CSS-first with `@theme` in `design-system/src/theme.css`, so they are also emitted as standard CSS custom properties (`--color-brand-700`, `--color-danger-50`, …). The file registers the component sources with `@source` so a portal's Tailwind build generates the classes the components use. React, React DOM, and Tailwind are peer dependencies.
- **Mobile:** not covered. Once HC-002 selects a mobile framework, that decision states how the mobile apps reuse the token values; React components are not assumed to be portable.

Usage and commands are documented in the [design-system README](../../design-system/README.md).

### Evidence

On 2026-10-10 with Node.js 24.13.0 / npm 11.6.2, Vite 8.3.4, React 19.3.0, Tailwind 4.3.3:

- In `design-system/`: `npm run build` (`tsc -b && vite build`) and `npm run lint` passed. The built showcase was rendered in headless Microsoft Edge at desktop width and in a 360px-wide frame without horizontal overflow.
- A throwaway `create-vite@9.2.1 react-ts` project outside the repository linked the package with a `file:` dependency. Without `resolve.dedupe`, the bundle contained two React copies and the page rendered nothing. With it, `npm run build` and `npm run dev` both rendered the components, `useId`-based label wiring worked, and Tailwind generated the design-system classes through the symlink.

This validates the toolchain and consumption path only. No portal in the repository has been scaffolded or wired to the package.

## Alternatives considered

- **`packages/design-system/` with root npm workspaces:** one install from the root and automatic deduplication, but it adds root JavaScript tooling to a polyglot repository and a generic `packages/` folder that repository rules discourage.
- **Shared tokens only, components per portal:** least coupling, but duplicates buttons, forms, and tables three times and makes visual drift likely.
- **Inside `apps/web/`:** violates the rule that `apps/` holds named products only.
- **Plain CSS with custom properties:** no extra dependency, but slower to build layouts and every portal would need its own utility conventions.
- **Mantine (component library):** fastest for complex widgets, but a heavy dependency whose components and theming do not carry over to a future mobile stack.

## Consequences

### Positive

- One visual language and one demo-labelling convention across all portals; HC-050, HC-070, and HC-090 can start from `AppShell`, `SideNav`, and the state components.
- No build or publish step: editing the design system is immediately visible in a portal's dev server.
- Tokens are plain CSS custom properties, so values stay readable outside Tailwind.

### Negative

- Each portal must remember the `resolve.dedupe` setting and install the design system's own dependencies for type-checking.
- Tailwind becomes a dependency of every portal; dependency versions can drift between the design system and portals until CI checks them.
- Changes to the design system affect all portals at once, with no versioning beyond Git.
- No automated component tests yet; validation relies on type-checking, lint, and the showcase.

## Follow-up

- HC-050, HC-070, HC-090: add the dependency, Tailwind, `resolve.dedupe`, and the stylesheet imports as described in the README.
- HC-002: decide how mobile apps consume token values.
- When product CI is configured, include `npm ci`, `npm run lint`, and `npm run build` for `design-system/`.
- The test runner (Vitest is the natural candidate) is still undecided and left to the first ticket that needs component tests.
