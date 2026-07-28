# Week 2 Evidence Layer — Frontend Technical Design (Evidence Inspector)

Status: Frozen for implementation  
Depends on:  
- `docs/architecture/week2-evidence-layer-architecture.md`  
- `docs/architecture/week2-evidence-layer-backend-technical-design.md`  
Host surface: Writing Studio Shell (`frontend/src/features/writing/`)

---

## 1) Goal

Ship **Evidence Inspector** as the Writing Studio killer feature:

> Select / hover a sentence → see supporting and contradicting EvidenceObjects, confidence band, paper + page link, and a short stored reasoning chain — or an honest “insufficient evidence” state.

Frontend stays thin: call `POST /api/evidence/explain` and render; **do not re-rank** evidence client-side.

---

## 2) Non-goals (UI)

- Guided AI generation / “write with AI”
- Citation style picker rebuild (Phase 2.3)
- Cross-paper reasoning chat
- Evidence Timeline (post-MVP)
- Client-side LLM calls

---

## 3) Information architecture

```text
WritingWorkspacePage
  ├── Editor (existing markdown / blocks)
  ├── Save / version chrome (existing)
  └── EvidenceInspectorPanel (new)
        ├── Sufficiency banner (sufficient | weak | insufficient)
        ├── EvidenceObject cards (accepted first, candidates labeled)
        ├── Paper / page deep link
        └── Reasoning chain (stored steps only)
```

Optional secondary: Evidence library drawer for project-level browse + accept/reject (can be Slice 2 if Inspector-only ships first).

---

## 4) Types (`frontend/src/features/writing/types/evidence.ts` or `features/evidence/`)

Align with backend DTO; prefer shared naming with contract fixtures.

```ts
export type ConfidenceBand = "low" | "moderate" | "high";
export type EvidenceStatus = "candidate" | "accepted" | "rejected" | "superseded";
export type Sufficiency = "sufficient" | "weak" | "insufficient";

export interface EvidenceObjectDTO {
  id: number;
  status: EvidenceStatus;
  confidence_band: ConfidenceBand;
  claim: string;
  quote: string;
  page: number | null;
  section: string;
  file_id: number;
  file_title?: string;
  relation: "supports" | "contradicts" | "related";
  study_type: string;
  study_quality: string;
  supports: string[];
  contradicts: string[];
  limitations: string[];
  provenance?: Record<string, unknown>;
}

export interface ExplainResponse {
  status: "ok";
  sufficiency: Sufficiency;
  sentence: {
    block_id: string;
    range_start?: number;
    range_end?: number;
    text: string;
  };
  evidence: EvidenceObjectDTO[];
  chain: Array<{ step: string; detail: string }>;
  warnings: string[];
}
```

Mappers live in `services/evidenceMappers.ts`; error map extends Writing `errorMap` patterns.

---

## 5) API client

Add to writing feature or `features/evidence/api.ts`:

- `explainEvidence(body)` → `POST /api/evidence/explain`
- `listEvidenceBindings(documentId)`
- `createEvidenceBinding(documentId, body)`
- `deleteEvidenceBinding(bindingId)`
- `reviewEvidence(evidenceId, body)` (if review UI in MVP)
- `enqueueEvidenceExtract(projectId, fileId)` (ops / library affordance)

Use existing `apiClient` + CSRF. Contract fixtures under `tests/fixtures/evidence/` mirrored for Vitest.

---

## 6) Editor integration

### Anchor strategy

1. Prefer stable `block_id` from editor block structure when available.
2. Else markdown character range (`range_start` / `range_end`) for current selection.
3. Always send `selected_text` as display hint — **server does not trust it alone** for authz or identity.

### Interactions

| Trigger | Behavior |
|---------|----------|
| Selection change (debounced) | Call explain; update Inspector |
| Click evidence card paper link | Open Library / Paper Workspace at `file_id` + page when deep-link exists |
| Empty selection | Inspector idle / last selection sticky (product choice: sticky preferred) |
| Explain returns insufficient | Show empty state copy — never invent bullet “evidence” |

### Binding UX (MVP)

- “Link evidence…” from Inspector when user picks an object from project list (if list UI present).
- Auto-suggestions deferred unless extract+bind pipeline is explicit in a later slice.

---

## 7) Evidence Inspector UI contract

### Sufficiency banner

- `sufficient` — at least one **accepted** supporting object (or policy: accepted OR high-band candidate — **prefer accepted-only for “supported” wording**).
- `weak` — only candidates / low band / contradicts present without supports.
- `insufficient` — no usable objects; copy: “Insufficient evidence for this sentence.”

### Card content (one job per card)

- Claim (primary)
- Quote (secondary, truncated)
- Confidence band chip (`low|moderate|high`) — not a fake percentage
- Status badge (`candidate` clearly labeled)
- Supports vs contradicts grouping
- Paper title + page
- Limitations list when present

### Chain

Render `chain[]` as ordered plain steps. If empty, omit section. Do not call a model to “improve” the chain in the client.

### Accessibility

- Inspector is a complementary region with `aria-live="polite"` for sufficiency changes.
- Keyboard: focusable cards; Esc closes expanded quote.
- Do not rely on color alone for supports vs contradicts.

### Visual language

Stay inside Writing Studio / Design System v2 patterns — no new marketing hero, no purple-glow AI aesthetic. Inspector is a working tool panel, not a dashboard of stats.

---

## 8) State

Extend writing store lightly or add `evidenceInspectorStore`:

- `selectionAnchor`
- `explainStatus` (`idle|loading|ok|error`)
- `explainResult`
- `lastError`

Do not duplicate full evidence library in client memory beyond current explain payload + optional bindings list.

Telemetry (privacy-safe): event names only + counts/bands — **no full quotes** in analytics payloads (`utils/telemetry` pattern from writing).

---

## 9) Error / empty UX

| Case | UI |
|------|-----|
| 401/403 | Existing auth / forbidden toast |
| 404 document | Navigate back to writing list |
| Network | Retry affordance |
| insufficient | Dedicated empty state (Principle 0) |
| Candidates only | Banner: “Unreviewed evidence — accept in review before treating as support” |

---

## 10) Test plan (frontend)

- Mapper unit tests from contract fixtures
- Inspector render: sufficient / weak / insufficient / candidate labeling
- Selection → debounced explain mock
- a11y: live region + keyboard card focus
- No client re-ordering assertions (order === API order)

---

## 11) File placement recommendation

```text
frontend/src/features/evidence/
  api.ts
  types.ts
  services/evidenceMappers.ts
  components/EvidenceInspectorPanel.tsx
  components/EvidenceObjectCard.tsx
  hooks/useEvidenceExplain.ts
```

Wire panel into `WritingWorkspacePage` without rewriting the shell.
