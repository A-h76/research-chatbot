# 09 — Developer B Notes

Running engineering log. Newest entries at top. This is a log, not a summary
document — see [CHANGELOG.md](CHANGELOG.md) for the dated record of actual changes,
and [HANDOFF.md](HANDOFF.md) for current async status.

---

### 2026-07-30 — Phase 1 review complete

Reviewed the full frontend codebase (`frontend/src/`, 25 feature folders, routing,
components, state, API layer, styling, testing, auth) and the full documentation
landscape (`docs/idd/`, `docs/contracts/`, `docs/epics/`, `docs/adr/`, `Now-Status/`,
top-level `docs/*.md`). No code changed. Key things worth remembering:

- **This is not a greenfield project and not a first architecture pass.** A same-day
  (2026-07-30) IDD/contracts/epics/Now-Status pack already exists, untracked, all
  "Proposed" and unsigned, built on top of 7 accepted-and-tracked ADRs. It already
  contains a Developer-B ticket list (EPIC-0001, B-001…B-009) that overlaps almost
  exactly with this charter's Phase-1 ask. Treated it as authoritative sequencing
  rather than inventing a parallel roadmap — see
  [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md).
- **The Evidence Platform API surface (the most architecturally critical part,
  frozen by ADR-0003/0005/0007) is already correctly wired up on the frontend** —
  found while directly reading `features/evidence/api.ts` against
  `docs/idd/IDD-0003-API-Contracts.md`. Good sign for whoever built it.
- **Found one concrete, fixable duplicate**: `WritingPage.tsx` line 348 calls
  `fetch("/api/writing", …)` raw, duplicating `writingApi.transform()` which already
  exists and wraps the identical endpoint through `apiClient`. Small, isolated,
  zero-contract-risk fix — a good Immediate-tranche candidate precisely because it
  doesn't touch anything else.
- **Found one real type-contract divergence worth flagging, not fixing myself**:
  `features/evidence/types.ts`'s `EvidenceObjectDTO` and IDD-0004 §3's
  `EvidenceObject` genuinely disagree on several fields (page range shape, presence
  of `study_type`/`study_quality`/`relation` vs. `evidence_type`/`finding`/
  `pipeline_version`). Recorded in
  [07-TypeScript-Type-Plan.md](07-TypeScript-Type-Plan.md) and
  [10-Risks-And-Questions.md](10-Risks-And-Questions.md) rather than guessed at.
- **`features/writing/state/writingStore.ts` has no actual store** — just a type and
  an initial-state constant. Either rename it or implement it; either is a small,
  isolated change.
- Did not touch the stale, chat-first root `README.md` — it's product documentation,
  not frontend architecture, and out of scope for this workspace, but noted in
  [00-Project-Overview.md](00-Project-Overview.md) since it could mislead a new
  contributor about what Dhund currently is.
- No implementation started. Waiting for user confirmation per the charter's
  "Final Instruction" before touching any code.
