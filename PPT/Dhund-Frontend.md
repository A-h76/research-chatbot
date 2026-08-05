# Dhund — Frontend

> SPA map for slides / notes. Audited from `frontend/` 2026-08.

---

## Stack

| Piece | Choice |
|-------|--------|
| Framework | React 19 + TypeScript |
| Build | Vite (`frontend/`) |
| Styling | Tailwind v4 + shadcn/ui (`@base-ui/react`) |
| Motion | Framer Motion (product); landing motion is intentionally scarce |
| Routing | `frontend/src/routes/router.tsx` + `RootLayout` |
| API | `lib/apiClient.ts` · SSE `lib/sse.ts` |
| Dev | Vite `:5173` proxies `/api` `/auth` `/login` → Flask `:5000` |
| Prod | Flask serves `frontend/dist` |

**Landing** is separate: Jinja `templates/login.html` + `static/landing-v2.css` (not the SPA).

---

## Design language (what the UI must feel like)

| Surface | Feeling | Borrow |
|---------|---------|--------|
| App shell / library / search | Dense, hairline, calm | Linear + Vercel |
| Writing / notes | Long-form calm, ~65ch | Notion |
| Evidence | Canvas + inspector | Figma + Linear |
| Docs (`/docs`) | Sidebar · prose · TOC | Mintlify |
| Pipeline / AI stages | Scoped stage chips only | Cursor discipline (not Cursor orange) |
| Landing | Section-owned brands | Tesla hero → … → SpaceX trust → Stripe pricing |
| Trust marketing | Black/white austerity | SpaceX Trust Layer only |

**Accent:** Dhund **signal teal** only. No purple, mesh skies, cream-as-brand.

Governance: `docs/DHUND-DESIGN-LANGUAGE-v1.md`.

---

## Route map

| Route | Surface |
|-------|---------|
| `/` | Projects hub (authenticated) |
| `/home` | Dashboard — “What should I do next?” |
| `/projects` · `/projects/:id` | Projects list + detail console |
| `/library` (`/files`) | Library, upload, Connect, collections |
| `/papers/:fileId` · `/papers/:fileId/chat` | Paper workspace + paper chat |
| `/research/compare` | Multi-paper analysis |
| `/writing` | Writing Studio |
| `/citations` | Citation table / BibTeX |
| `/notes` | Notes |
| `/memory` | Memory |
| `/search` | Discover / search |
| `/chat` · `/c/:id` | Streaming chat |
| `/settings` | Account, research defaults, integrations, data |
| `/admin` | Admin SPA (flags, invites, quotas, kill switch, …) |
| `/docs` · `/docs/:slug` | In-app Mintlify-style docs |
| `/support` · legal | Support + privacy/terms |

Logged-out `/` → marketing landing (`login.html`).

---

## Feature folders (`frontend/src/features/`)

| Folder | Owns |
|--------|------|
| `dashboard` | Home maturity, next actions, upload hero |
| `projects` | Project list/detail, papers, notes, questions, research console |
| `files` | Library cards, collections, Connect, upload dialogs, health strip |
| `papers` | Overview tabs, evidence/entities/narrative, pipeline card, paper chat |
| `evidence` | Matrix, graph, themes, timeline, inspector, extract/reason hooks |
| `writing` | Studio, outline, grounded draft verify, reviewer panel, progress |
| `chat` | Composer, stream hook, conversation view, skill picker |
| `citations` | Table + forms |
| `notes` · `memory` | Notes list; memory page |
| `search` | Discover API + search page |
| `pipeline` | AI state badges, stepper/chips, processing hooks |
| `research-flow` | Ecosystem Icon Cloud / beams (also landing island) |
| `analysis` | Multi-paper / compare UI |
| `settings` · `profile` · `onboarding` | Prefs, me hook, wizard |
| `admin` | Gates + ops panels |
| `docs` | Catalog imports living `docs/` contracts via `@repo-docs` |
| `ai` · `models` | Prompt/API explainers, model UI |
| `legal` · `support` | Static legal content, support |
| `sidebar` · layout components | Shell, command palette, account menu |

Shared UI: `frontend/src/components/ui/*`, layout under `components/layout/`.

---

## Key UX patterns

### Evidence inspector
- Main canvas = passage / claim content  
- Side rail = provenance, confidence band, source meta  
- Components: `ConfidenceBandBadge`, `ProvenanceStrip`, inspector panel  

### Pipeline honesty
- Stage chips (`sem.*` / AI state) — scoped color, not rainbow chrome  
- `PipelineStepper` / `ResearchProgressStage`  

### Writing
- Cool paper background, readable measure  
- Grounded drafts + citation insert  
- Research Reviewer panel  

### Library
- Dense rows / cards without heavy elevation  
- Health strip, duplicates, Connect catalog honesty (Live vs Coming soon)  

### Docs
- Three-column Mintlify layout  
- Bodies imported from repo `docs/contracts` + ADRs (`?raw`)  

---

## Landing (marketing) — section ownership

Implemented in `templates/login.html` + `static/landing-v2.css`:

| Section | Brand mix |
|---------|-----------|
| Hero | Tesla 70 / Apple 30 |
| Product story | Apple / Vercel |
| Pipeline | Linear / Together |
| Ecosystem | SpaceX + Icon Cloud island |
| AI Router | Replicate dark well |
| Workspace / Evidence | Linear + Figma |
| Writing | Notion |
| Docs tease | Mintlify |
| Trust | SpaceX |
| Pricing | Stripe-simple placeholders |
| FAQ | Mintlify accordion |
| Finale | Superhuman deep teal |
| Footer | Vercel minimal |

Motion allowed: hero fade, pipeline beam, ecosystem connections, router cascade, frame enter.  
Forbidden: neon particles, floating icon spam, infinite loops.

---

## Auth UX

| Action | Target |
|--------|--------|
| Start Research / Sign up | `/auth/sign-up` |
| Log in (landing) | `#signin` or `/auth/sign-in` |
| Google | `/auth/google` |
| Magic link | `POST /auth/magic-link` |
| Dev skip | `/api/dev-login` (non-prod) |

SPA assumes session cookie after login; profile via `useMe` / `/api/me`.

---

## Build notes

- `npm run build` → `tsc -b && vite build`  
- Docker frontend stage must `COPY docs/ /docs/` because catalog imports `@repo-docs` → `../docs`  
- Ecosystem island: Vite entry `ecosystem.html` mounted into Jinja `#dhund-ecosystem-cloud`  

---

## Slide prompts

1. SPA stack + proxy diagram  
2. Route map (researcher journey)  
3. Evidence inspector screenshot callout  
4. Feature folder → product area  
5. Design language grid (5 surfaces)  
6. Landing section formula  
7. Docs Mintlify layout  

---

## Source paths

- `frontend/src/routes/router.tsx`  
- `frontend/src/features/*`  
- `frontend/src/index.css`  
- `templates/login.html` · `static/landing-v2.css`  
- `docs/DHUND-DESIGN-LANGUAGE-v1.md`  
