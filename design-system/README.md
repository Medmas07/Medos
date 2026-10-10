# Design System

## Purpose and status

Shared visual foundation for the three web portals ([Hospital](../apps/web/hospital-portal/README.md), [Governance](../apps/web/governance-portal/README.md), [Research](../apps/web/research-portal/README.md)), delivered by HC-004 ([#27](https://github.com/Medmas07/Hackcure_hackathon/issues/27)) at depth D1. Location and styling are decided in [ADR-0002](../docs/decisions/ADR-0002-web-design-system.md).

- **IMPLEMENTED:** design tokens, base typography, and the React components listed below, plus a showcase page.
- **Checked on 2026-10-10:** `npm run build` (type-check and showcase build) and `npm run lint` pass; the showcase renders at desktop and 360px widths; a throwaway Vite portal outside the repository consumed the package through a `file:` dependency, and both `npm run build` and `npm run dev` rendered the components with working hooks. No portal in this repository consumes it yet, and there are no automated component tests.
- **IMPLEMENTED (2026-10-11, UI redesign):** mint visual system (brand `#A7E3D4`) with light and dark themes, a theme toggle, a responsive shell with a mobile navigation drawer, `StatCard`, `Skeleton`, and CSS-only motion. A scripted WCAG check of the main text/background token pairs passes AA in both themes; this is not a formal accessibility audit.
- **Not covered:** mobile apps (framework OPEN, HC-002), client-side routing integration, formal accessibility audit, and automated component tests.

## Responsibilities

- Design tokens in [`src/theme.css`](src/theme.css): the mint `brand` scale, semantic neutrals (`paper`, `surface`, `surface-raised`, `surface-muted`, `line`, `line-strong`, `ink`, `ink-soft`, `ink-muted`, `primary`, `on-primary`, `chrome`), status tones (`info`, `success`, `warning`, `danger`, `demo`), radii, shadows, easing, fonts, and base typography. Spacing uses Tailwind's default 4px scale.
- Presentational React components: `Button`, `TextField`, `SelectField`, `TextareaField`, `CheckboxField`, `Card`, `StatCard`, `Table`, `Badge`, `Alert`, `AppShell`, `SideNav`, `PageHeader`, `LoadingState`, `EmptyState`, `ErrorState`, `Spinner`, `Skeleton`, `Timeline`, `ThemeToggle`.
- Theme preference: `useTheme()` / `setThemePreference()` store the light/dark/system choice in `localStorage` (`hc-theme`). This is a UI preference only.
- Explicit demo labelling: `DemoBanner`, `DemoBadge`, and the `demo` tone mark MOCKED or fictional content so it is never presented as production behaviour.

## Non-responsibilities

The design system holds no domain logic, data fetching, API clients, routing, authentication, or fixtures. Portals map their own statuses (for example "Pending review") to a `Tone`. Canonical demo data lives in [`demo-data/`](../demo-data/README.md); [`showcase/placeholder-data.ts`](showcase/placeholder-data.ts) is showcase-only placeholder text.

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
import { defineConfig, searchForWorkspaceRoot } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Lets the dev server serve the design system's self-hosted font files.
  server: { fs: { allow: [searchForWorkspaceRoot(process.cwd()), '../../../design-system'] } },
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

Portals keep using Tailwind utilities for page layout, with the same tokens. Prefer the semantic names (`bg-surface`, `text-ink-soft`, `border-line`) and tone pairs (`bg-warning-50 text-warning-700`); avoid raw Tailwind palettes (`amber-*`, `emerald-*`), which do not follow the theme.

## Theming

Light is the default; dark applies when `<html data-theme="dark">`. Dark values are defined once in `theme.css` and reused inside `.hc-chrome` (the always-dark sidebar), so content there reads correctly in both themes.

- **Brand use:** on white, `brand-700` is the text/icon colour, `brand-800` (`primary`) the solid fill, and `brand-600` focus rings and borders; `brand-300` (`#A7E3D4`) and the 50–200 tints are fills, highlights, and active states. In dark, the 50–200 and 700–900 steps flip so the same utilities stay readable; `primary` becomes mint with dark text.
- **Status tones:** 50 background, 200 border, 600 solid marker, 700 text, 800 strong text. The 50/200/700/800 steps flip in dark; 600 does not. `demo-solid` sits behind white text (`DemoBanner`) in both themes.
- **`slate-*`:** redefined as teal-tinted neutrals that also flip in dark, so existing `text-slate-900` / `bg-slate-50` utilities follow the theme. New code should use the semantic names.

Add this to the `<head>` of each portal's `index.html`, before any stylesheet, so the page never flashes the wrong theme:

```html
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#f7fbfa" />
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#071a17" />
<script>
  (function () {
    var dark = window.matchMedia('(prefers-color-scheme: dark)').matches
    var saved = null
    try {
      saved = window.localStorage.getItem('hc-theme')
    } catch (e) {}
    document.documentElement.dataset.theme =
      saved === 'light' || saved === 'dark' ? saved : dark ? 'dark' : 'light'
  })()
</script>
```

Then pass `toolbar={<ThemeToggle />}` to `AppShell`. The `dark:` variant follows `data-theme`.

## Motion

CSS only, no animation library. Only `transform` and `opacity` animate, with short ease-out curves (`--ease-out`). `prefers-reduced-motion: reduce` disables all of it.

| Utility / prop | Effect |
|---|---|
| `hc-stagger` on a grid or list | children rise in (opacity + 8px, 320ms), 40ms apart, up to 8 steps |
| `Card interactive`, `StatCard onClick`, `hc-lift` | 2px hover lift; the deeper shadow fades in on a pseudo-element (pointer devices only) |
| `hc-press` | scale 0.97 while pressed |
| `AppShell pageKey` | content fades and rises (260ms) when the key changes |
| `ThemeToggle` | cross-fades the theme through the View Transitions API where supported |
| `hc-skeleton`, `Skeleton`, `LoadingState variant="skeleton"` | 1.3s shimmer placeholder |

## Fonts

Geist (interface) and Instrument Serif (`h1` and `StatCard` figures, through `font-display`) are self-hosted from `@fontsource-variable/geist` and `@fontsource/instrument-serif`, imported by `theme.css`. Pages make no font CDN request.

## Usage rules

- Show `DemoBanner` on every portal page while any data or integration is MOCKED, and `DemoBadge` on individual simulated values such as mock AI output or simulated ledger proofs.
- Give every data view loading, empty, and error states (`LoadingState`, `Table` `empty`, `ErrorState`).
- Use `StatCard` only for figures the portal already computes; do not add invented trends or deltas.
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
