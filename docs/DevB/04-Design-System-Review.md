# 04 — Design System Review

**Status:** Draft for review · **Principle: extend, do not replace, per charter.**

## Source of truth

`frontend/src/index.css` (534 lines), Tailwind v4 CSS-first config — no
`tailwind.config.js/ts` file exists; tokens are plain CSS custom properties. Referenced
by the codebase as governed by an external doc, `docs/DESIGN-SYSTEM-v2.md` (see the
`--primary` token comment below), which I have not yet fully cross-read against the
CSS — flagged as a follow-up in
[10-Risks-And-Questions.md](10-Risks-And-Questions.md) rather than assumed.

## Typography

Type scale is token-based: `--type-display`, `--type-title`, `--type-body`,
`--type-ui`, `--type-meta`, `--type-micro`. Custom self-hosted font, "Creato Display,"
loaded via `@font-face` from `/static/fonts/...` (served by the Flask backend per
`vite.config.ts`'s proxy list — a real cross-boundary dependency: the frontend's type
system depends on the backend serving static font files, worth knowing before any
deploy-topology change).

## Spacing

Token-based scale: `--space-1` through `--space-8`. Consistent custom-property
approach, no arbitrary magic-number spacing found in the token layer itself (feature
components weren't individually audited for hardcoded spacing values in this pass).

## Color system

Full shadcn semantic set present: `--background`, `--foreground`, `--card`,
`--popover`, `--primary`, `--secondary`, `--muted`, `--accent`, `--accent-soft`,
`--destructive`, `--border`, `--input`, `--ring`, `--hover`. Plus three
**domain-specific token groups** layered on top of the generic shadcn set:

1. **Sidebar tokens** (`--sidebar*`) — dedicated palette for the nav shell.
2. **Chat tokens** (`--user-bubble*`) — dedicated palette for message bubbles.
3. **Surface tokens** (`--surface-app/panel/sunken`) — a layering system beyond plain
   `background`/`card`.
4. **"AI State Language" palette** (`--sem-ready`, `--sem-running`, `--sem-queued`,
   etc.) — explicitly scoped by comment to "chart/pipeline chrome only," i.e. status
   indicators for async job/pipeline state, not general UI color.

Notably, `--primary` carries an explicit design decision in its own comment: `#0f6e6a`
(teal), "distinct from consumer-AI violet — DESIGN-SYSTEM-v2 §8" — a deliberate choice
to visually differentiate Dhund from "consumer AI chat" products, which lines up
exactly with the charter's "NOT: AI Chat, Prompt Playground, Magic Generation" design
philosophy. This is already-implemented brand intent, not something to introduce.

A `.dark` variant block exists (confirmed by `@custom-variant dark (&:is(.dark *))`
and `ThemeToggle.tsx`/`ThemeContext.tsx`) but wasn't read line-by-line in this pass —
noted so no claim is made about dark-mode token parity without verifying it.

## Icons

`lucide-react` (`^1.24.0`) exclusively — confirmed as `iconLibrary: "lucide"` in
`components.json`, no `@radix-ui/react-icons` or mixed icon sets found.

## Buttons / Forms

Standard shadcn primitives (`button`, `input`, `input-group`, `label`, `select`,
`switch`, `slider`, `textarea`) via `@base-ui/react`, using
`class-variance-authority` for variants (a `cva` dependency is present) — this is the
conventional, expected shadcn pattern, no deviation found.

## Responsive behavior

`hooks/useMediaQuery.ts` (+ `useIsMobile`) exists and is presumably the mechanism
behind `components/layout/MobileDrawer.tsx`'s mobile-vs-desktop nav split. Not
independently verified against every feature page in this pass — flagged as an
activity for Sprint work (manual responsive pass), not a documentation-only fact.

## Accessibility

No axe/Lighthouse audit was run as part of this documentation phase (that's testing
activity, not review). What's structurally true: shadcn/`@base-ui/react` primitives
carry better default focus/keyboard/ARIA semantics than hand-rolled equivalents, so
most of the app inherits reasonable a11y defaults "for free" wherever it uses
`components/ui/*`. The two areas most likely to need dedicated attention because
they're fully custom (not primitive-derived): the 40+-file visx chart kit
(`components/charts/`) and the hand-built `Sidebar.tsx` (536 lines, nav/collapse/list
logic). Recorded as an open item, not yet assessed, in
[10-Risks-And-Questions.md](10-Risks-And-Questions.md).

## Consistency

- The token system itself is consistent and appropriately layered (generic shadcn →
  domain-specific groups) rather than components each inventing their own colors.
- The one identified *inconsistency* is structural, not visual: **Card/Panel
  components are independently implemented per feature rather than composed from a
  shared primitive** (see [03-Component-Inventory.md](03-Component-Inventory.md)) —
  this is a component-architecture issue, not a design-token issue; the tokens
  themselves are applied consistently within each implementation.

## Recommendation posture

Per the charter ("Never redesign without justification. Extend. Do not replace."):
no token, color, or typography changes are proposed here. The one actionable design-
system item from this review is component-level (shared `Panel` primitive), already
captured in [03](03-Component-Inventory.md) and sequenced in
[05-Frontend-Roadmap.md](05-Frontend-Roadmap.md).
