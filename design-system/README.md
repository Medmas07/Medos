# Design System

## Purpose and status

Shared visual foundation for the three web portals ([Hospital](../apps/web/hospital-portal/README.md), [Governance](../apps/web/governance-portal/README.md), [Research](../apps/web/research-portal/README.md)), delivered by HC-004 ([#27](https://github.com/Medmas07/Hackcure_hackathon/issues/27)) at depth D1. Location and styling are decided in [ADR-0002](../docs/decisions/ADR-0002-web-design-system.md).

- **IMPLEMENTED:** design tokens, base typography, and the React components listed below, plus a showcase page.
- **Checked on 2026-10-10:** `npm run build` (type-check and showcase build) and `npm run lint` pass; the showcase renders at desktop and 360px widths; a throwaway Vite portal outside the repository consumed the package through a `file:` dependency, and both `npm run build` and `npm run dev` rendered the components with working hooks. No portal in this repository consumes it yet, and there are no automated component tests.
- **Not covered:** mobile apps (framework OPEN, HC-002), dark mode, client-side routing integration, and formal accessibility audit.

## Responsibilities

- Design tokens: brand and status colours (`info`, `success`, `warning`, `danger`, `demo`), fonts, and base heading/body typography in [`src/theme.css`](src/theme.css). Neutrals use Tailwind's `slate` scale; spacing uses Tailwind's default 4px scale.
- Presentational React components: `Button`, `TextField`, `SelectField`, `TextareaField`, `CheckboxField`, `Card`, `Table`, `Badge`, `Alert`, `AppShell`, `SideNav`, `PageHeader`, `LoadingState`, `EmptyState`, `ErrorState`, `Spinner`, `Timeline`.
- Explicit demo labelling: `DemoBanner`, `DemoBadge`, and the `demo` tone mark MOCKED or fictional content so it is never presented as production behaviour.

## Non-responsibilities

The design system holds no domain logic, data fetching, API clients, routing, authentication, or fixtures. Portals map their own statuses (for example "Pending review") to a `Tone`. Canonical demo data belongs to HC-005, not here; [`showcase/placeholder-data.ts`](showcase/placeholder-data.ts) is showcase-only placeholder text.

## Commands

From inside `design-system/` (Node.js and npm as in [ADR-0001](../docs/decisions/ADR-0001-web-frontend-technology.md)):

| Purpose | Command |
|---|---|
| Install dependencies | `npm install` |
| Showcase dev server on <http://localhost:5179> | `npm run dev` |
| Type-check and build the showcase | `npm run build` |
| Lint | `npm run lint` |
| Preview the built showcase | `npm run preview` |

## Using it from a portal

Portal shell tickets (HC-050, HC-070, HC-090) wire this up after scaffolding. From inside `apps/web/<portal>/`:

```bash
npm install -D tailwindcss@^4 @tailwindcss/vite@^4
npm install ../../../design-system
```

`npm install <path>` records `"@hackcure/design-system": "file:../../../design-system"` and symlinks the folder; portals compile its TypeScript source directly. Run `npm install` inside `design-system/` once as well; its own dependencies are needed for type-checking.

`vite.config.ts`. The `dedupe` line is **required**: without it the linked source loads a second React copy and the page renders blank.

```ts
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { dedupe: ['react', 'react-dom'] },
})
```

Main stylesheet, for example `src/index.css` (replace the template styles):

```css
@import "tailwindcss";
@import "@hackcure/design-system/theme.css";
```

Components:

```tsx
import { AppShell, Button, DemoBanner, SideNav } from '@hackcure/design-system'
```

Portals keep using Tailwind utilities for page layout, with the same tokens (for example `bg-brand-700`, `text-danger-700`).

## Usage rules

- Show `DemoBanner` on every portal page while any data or integration is MOCKED, and `DemoBadge` on individual simulated values such as mock AI output or simulated ledger proofs.
- Give every data view loading, empty, and error states (`LoadingState`, `Table` `empty`, `ErrorState`).
- Never rely on colour alone: badges, alerts, and timeline items always carry text.
- One primary `Button` per view; `danger` only for destructive or rejecting actions.
- Do not add domain-specific components here (for example a medication-warning panel). Build them in the portal from these primitives, and move something here only when two portals need it.

## Layout

```text
design-system/
  src/            package source: index.ts (public API), theme.css (tokens), components/
  showcase/       showcase page and its placeholder content (not exported)
  index.html      showcase entry point
```
