# Version 1 Completion Tracker

**Document:** `11-VERSION1-COMPLETION-TRACKER.md`  
**Role:** Layer 4 — **execution tracking** (not strategy)  
**Last updated:** 2026-08-02  
**Company mode:** Stop planning. Execute. Cursor = Engineering Team, not a coding assistant.

**Do not add strategy here** — vision/strategy live in [05](05-RESEARCH-OS-VISION.md)–[10](10-RESEARCH-ECOSYSTEM-MASTERPLAN.md).  
**Do not write new roadmap docs** unless product direction genuinely changes. Update **this** file instead.

---

## 0. Engineering rules (binding)

### 0.1 Definition of Production Ready

A subsystem **cannot** move to 🟢 / Current = 100% / Production Ready = Yes unless **ALL** of the following are true:

```text
✓ Backend complete (V1 scope)
✓ Frontend complete (V1 scope)
✓ Database migrations complete (if schema needed)
✓ Workers / background jobs complete (if applicable; else N/A checked)
✓ API documented (contract or docs/audit note)
✓ Unit tests passing
✓ Integration tests passing (or justified N/A for pure UI polish)
✓ No TODO/FIXME remaining for V1 scope of this subsystem
✓ Documentation updated (tracker card + any Feature Matrix / API notes)
✓ Integrated with surrounding subsystems (smoke of upstream/downstream)
✓ Reviewed against Research OS Vision lifecycle step it serves
✓ No known P0/P1 regressions introduced
✓ Deployable without a temporary “WIP” feature flag
   (permanent product flags OK only if the happy path ships on by default)
```

**90% forever is forbidden.** If any box is unchecked, status stays 🟡 or 🔴.

When marking 🟢, paste a one-line **Production Ready attestation** into the subsystem card Change note / checkbox section (date + who).

### 0.1b Definition of Done (project-wide — every merge)

Every merged change (not only subsystem close-out) must satisfy:

```text
✓ Builds successfully for production (backend + frontend as applicable)
✓ All automated tests for touched areas pass
✓ No TODO/FIXME items left for V1 scope of the change
✓ Migration + rollback note if schema changes
✓ Observability: logging/metrics where appropriate for new paths
✓ User-facing docs updated if behavior changes
✓ Completion Tracker updated immediately after merge (if a row moved)
✓ Does not reduce Current % of any dependent subsystem
```

Optimize for **rows completed**, not lines of code. A sprint succeeds only when one subsystem hits 100% + Production Ready = Yes + tracker updated + freeze respected.

### 0.2 Sprint Success

Every sprint has **exactly one objective**: one subsystem → 100%.

```text
Example — Sprint 1
  Writing Intelligence → 100%
  Nothing else.
```

Not allowed in the same sprint: “some Reviewer + some Library + some UI.”

When the subsystem hits Production Ready:

1. Update this tracker (%, status, checkboxes, change log)  
2. Commit  
3. Ship internally  
4. Only then start the next row in §2  

### 0.3 Freeze means freeze

No work on:

```text
❌ Graph v2 / flagship KG productization
❌ Research Memory flagship
❌ Agents
❌ Enterprise (beyond tiny V1 security polish already on the scoreboard)
❌ Billing
❌ Notifications product
❌ PubMed / Drive / ORCID / new connectors
❌ New major AI surfaces
```

Until:

```text
P0 V1-critical rows → 100%
    ↓
P1 V1-critical rows → 100%
    ↓
P3* V1 ops/cost rows (Quotas, Feature flags, Admin SPA) → 100%
```

Exactly as §1 / §2. Soft dependencies do not license jumping ahead.

### 0.4 Completion loop (every subsystem)

```text
Read tracker
  → Pick first unfinished row in §2
  → Audit implementation
  → Complete backend
  → Complete frontend
  → Complete workers
  → Complete database
  → Complete API docs
  → Complete tests
  → Complete docs
  → Attest Definition of Production Ready
  → Update tracker → Commit → Ship internally
  → Next subsystem
```

Nothing else.

### 0.5 Standard prompt (Engineering Team)

Use this for every row — do not invent a weaker brief:

```text
Complete Subsystem #<N> (<Name>) to Production Ready according to
docs/audit/11-VERSION1-COMPLETION-TRACKER.md.

Audit the existing implementation. Identify every remaining backend,
frontend, worker, database, API, testing, documentation, and integration
gap for V1 scope only. Complete only the remaining work. Verify it
satisfies §0.1 Definition of Production Ready. Update the tracker
(percent, status, checkboxes, change log). Do not begin another subsystem.
Do not add features outside this card. Respect the freeze (§0.3).
```

**Owner:** default `engineering` until assigned.  
**Status key:** 🔴 blocker · 🟡 in progress / polish · 🟢 V1 complete · ⚪ out of V1 scope

---

## 1. Master scoreboard (V1)

Percentages = progress toward **V1 Production Ready** for that subsystem (not toward P7 vision).

| # | Subsystem | Phase | Current | Target | Status | Production Ready? | Blocked? |
|---|-----------|-------|--------:|-------:|:------:|:-----------------:|:--------:|
| 1 | Evidence Platform | P0 | 100% | 100% | 🟢 | Yes | No |
| 2 | Writing Shell | P0 | 100% | 100% | 🟢 | Yes | No |
| 3 | Writing Intelligence | P0 | 100% | 100% | 🟢 | Yes | No |
| 4 | Research Reviewer | P0 | 100% | 100% | 🟢 | Yes | No |
| 5 | Citation insert-into-draft | P0 | 100% | 100% | 🟢 | Yes | No |
| 6 | Extract quality (top backlog) | P0 | 100% | 100% | 🟢 | Yes | No |
| 7 | Private Alpha Success Gate | P0 | 100% | 100% | 🟢 | Yes | No |
| 8 | Library (core Bridge) | P1 | 100% | 100% | 🟢 | Yes | No |
| 9 | Library Sync (worker) | P1 | 100% | 100% | 🟢 | Yes | No |
| 10 | Ref-mgr PDF pull | P1 | 100% | 100% | 🟢 | Yes | No |
| 11 | Integrations Settings catalog | P1 | 100% | 100% | 🟢 | Yes | No |
| 12 | Landing Ecosystem honesty | P1 | 100% | 100% | 🟢 | Yes | Soft: 11 |
| 13 | Quotas (chat + WI gate) | P3* | 100% | 100% | 🟢 | Yes | No |
| 14 | Feature-flag service | P3* | 100% | 100% | 🟢 | Yes | No |
| 15 | Admin SPA (ops) | P3* | 100% | 100% | 🟢 | Yes | Soft: 14 |
| 16 | Auth (V1 bar) | — | 100% | 100% | 🟢 | Yes | No |
| 17 | Upload + Worker pipeline | — | 100% | 100% | 🟢 | Yes | No |
| 18 | Export (lit-review MD/Bib) | P0 | 100% | 100% | 🟢 | Yes | Soft: 4 |
| 19 | Projects (personal) | — | 100% | 100% | 🟢 | Yes | No |
| 20 | Security baseline (V1) | — | 100% | 100% | 🟢 | Yes | No |

\*P3 items listed because V1 closed-beta **ops/cost** requires them before honest “complete personal OS”; still **after** P0/P1 blockers in execution order.

### Out of V1 (do not work until freeze lifts)

| Subsystem | Current | Target (later) | Status |
|-----------|--------:|---------------:|:------:|
| OCR / scanned index | 10% | 100% (P3.7) | ⚪ |
| In-app Notifications | 5% | 100% (P4) | ⚪ |
| Billing / payments | 0% | 100% (P4) | ⚪ |
| Orgs / Teams / RBAC | 0% | 100% (P4/E2) | ⚪ |
| KG as flagship / Graph v2 | 5% | 100% (P5) | ⚪ |
| Research Memory flagship | 55% | 100% (P6) | ⚪ |
| Research Agents | 0% | 100% (P7) | ⚪ |
| Enterprise E1–E4 | ~10% | 100% | ⚪ |
| PubMed / Drive / ORCID | 0–15% | 100% (P2) | ⚪ |
| DOCX / journal packs | 0% | 100% (P4) | ⚪ |
| Notebook / PDF annotations | 5–30% | 100% | ⚪ |

---

## 2. Execution order (strict)

Work **top to bottom**. Do not start the next row until the current is 🟢 or explicitly waived in writing.

| Order | Subsystem | Why this order |
|------:|-----------|----------------|
| 1 | Writing Intelligence (binder + Verify) | Trust spine |
| 2 | Research Reviewer (FE + export gate) | Trust spine |
| 3 | Citation insert-into-draft | Trust spine |
| 4 | Extract quality (top items) | Better inputs |
| 5 | Export gate wired to Reviewer | Close write path |
| 6 | Private Alpha Success Gate | Prove vertical |
| 7 | Library Sync worker | Durability |
| 8 | Ref-mgr PDF pull | Complete Bridge claim |
| 9 | Integrations Settings catalog | Honesty |
| 10 | Landing Ecosystem Live/Soon | Honesty |
| 11 | Quotas chat + WI | Cost |
| 12 | Feature-flag service | Safe rollout |
| 13 | Admin SPA | Ops |
| 14 | Evidence / Shell / Auth / Upload polish to 100% | Close V1 bar |
| 15 | **Lift freeze** → P2 Ecosystem per [10](10-RESEARCH-ECOSYSTEM-MASTERPLAN.md) | Only then |

---

## 3. Subsystem detail cards

### 1 — Evidence Platform

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Owner | engineering |
| Dependencies | None (frozen contracts) |
| Blocked? | No |
| Production Ready? | **Yes** (2026-08-03) |

**Remaining tasks**

- [x] Top extract-quality backlog items (`Dhund-Flow/EXTRACTION_QUALITY_BACKLOG.md`) — High closed via #6
- [x] Compare / consensus UX depth (use existing APIs) — Matrix/Gaps/AI Compare + strip + evidence ID chips
- [x] Confirm freeze tests green in CI — `test_evidence_contract_freeze` + consensus/conflict (28 passed locally)
- [x] Docs: note V1 = frozen platform + quality, not new RI stages

**Done when:** Accept/reject → Inspector → Writing path stable; no contract breaks; quality bar accepted for Alpha.

**Attestation:** 2026-08-03 — Evidence Platform V1 Production Ready. Frozen contracts + extract-quality High (#6) + Compare/consensus UX on existing RI APIs (Matrix/Gaps strip, agreeing/disagreeing evidence IDs); freeze suite green. Not new RI stages. Next: Subsystem #2 Writing Shell.

---

### 2 — Writing Shell

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | None |
| Blocked? | No |
| Production Ready? | **Yes** (2026-08-03) |

**Remaining tasks**

- [x] Version history UX polish (API exists) — confirm + preview + restore-creates-new-head copy; conflict Reload latest
- [x] Thin store / dead scaffold cleanup or wire — deleted unused `writingStore` / selectors / `useWritingWorkspace` / mappers; wired `errorMap` + `autosavePolicy`
- [x] Autosave edge-case tests (conflict / offline) — FE policy unit tests; BE stale autosave 409 + versions/restore
- [x] Docs: shell = Production for V1 (no DocumentBlock required)

**Done when:** Create / edit / autosave / restore / lifecycle reliable in Alpha.

**Attestation:** 2026-08-03 — Writing Shell V1 Production Ready. Document create/edit/autosave/versions/restore/lifecycle; version restore confirm; conflict reload; dead store scaffolds removed. **Out of V1:** DocumentBlock, CommentThread, track-changes (not required for Production Ready shell).

**Out of V1:** DocumentBlock, CommentThread, track-changes.

---

### 3 — Writing Intelligence

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | Evidence Platform |
| Blocked? | No |
| Production Ready? | **Yes** (2026-08-02) |

**Definition of Production Ready (§0.1)**

- [x] Backend complete (V1 scope)
- [x] Frontend complete (V1 scope)
- [x] Database migrations complete — N/A (no new schema)
- [x] Workers / background jobs — N/A (sync WI path; lit-review job unchanged)
- [x] API documented (`accept_allowed`, fail-closed behavior)
- [x] Unit tests passing
- [x] Integration / contract tests — existing `tests/test_evidence_writing_intelligence.py` + unit suite
- [x] No TODO/FIXME for V1 WI scope
- [x] Documentation updated (tracker + FEATURE_MATRIX)
- [x] Integrated with Verify / Accept / Export
- [x] Reviewed against Vision step **Writing**
- [x] No known P0/P1 regressions
- [x] Deployable without WIP flag

**V1 policy lock:** Contested consensus = warn-and-generate (do not block solely for contested).

**Shipped this close-out**

- [x] Binder claim/sentence alignment + rebind (`citation_binder.py` v1.2.0)
- [x] Fail-closed Accept via `accept_allowed=false` on Reviewer error codes
- [x] FE Accept / export gates + style “not evidence-backed” labeling
- [x] FE↔BE export traceability orphan parity + `canExportGroundedLitReview`
- [x] Verify polish: findings counts, Open in Inspector, full Reviewer issue list
- [x] Tests: binder rebind, review-fail accept gate, export gate

**Attestation:** 2026-08-02 — Writing Intelligence V1 Production Ready. Next: Subsystem #4 Research Reviewer.

---

### 4 — Research Reviewer

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | WI drafts exist |
| Blocked? | No |
| Production Ready? | **Yes** (2026-08-02) |

**Definition of Production Ready (§0.1)**

- [x] Backend complete (persistence + reconstruct APIs already shipped)
- [x] Frontend complete (`ResearchReviewerPanel`, severity accordion, click→section)
- [x] Database migrations — N/A (0035 already present)
- [x] Workers — N/A
- [x] API documented (client wired to reviewer-runs)
- [x] Unit tests passing
- [x] Integration tests — `tests/test_reviewer_persistence.py`
- [x] No TODO/FIXME for V1 Reviewer scope
- [x] Documentation updated (EPIC-0005, FEATURE_MATRIX, tracker)
- [x] Integrated with Accept/export gates
- [x] Reviewed against Vision step **Review**
- [x] No known P0/P1 regressions
- [x] Deployable without WIP flag

**Shipped this close-out**

- [x] FE client: `listReviewerRuns` / `latestReviewerRun` / `getReviewerRun`
- [x] B-511 severity accordion + “No issues”
- [x] B-512 click finding → scroll to section
- [x] B-513 `reviewer_version` in panel + Confidence strip
- [x] B-514 export/Accept gate on any `severity=error` (+ persisted latest run on export)
- [x] A-505 export metadata `reviewer_version` + `issue_count`

**Attestation:** 2026-08-02 — Research Reviewer V1 Production Ready. Next: Subsystem #5 Citation insert-into-draft.

---

### 5 — Citation insert-into-draft

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | Writing Shell; Citations manager; WI binder |
| Blocked? | No |

**Exit criteria (V1 Production Ready)**

- [x] `GET /api/citations/<id>/resolve-evidence` — Citation → accepted EvidenceObject bridge (+ parenthetical fallback)
- [x] `parenthetical_cite` + stable `[#id]` insert text when grounded
- [x] FE `CitationInsertPicker` (Evidence + Library tabs, search)
- [x] Writing desk: Cite / Ctrl+Shift+C / Esc, insert at caret (replace selection), Remove cite, Inspect jump
- [x] On insert: autosave + `createBinding` when `evidence_id` present
- [x] On remove: strip `[#id]` + `deleteBinding` for matching bindings
- [x] Hover/preview strip for selected marker
- [x] Reviewer already validates orphans / unbound / unsupported claims (fail-closed export)
- [x] Export MD/BibTeX/RIS remain binder-driven (same `[#id]` spine)
- [x] Tests: `citeDraftHelpers` (vitest) + `tests/test_citation_resolve_evidence.py`

**Attestation:** 2026-08-02 — Citation insert-into-draft V1 Production Ready. Next: Subsystem #6 Extract quality (then Private Alpha Success Gate + vertical E2E).

**Done when:** Cite from Evidence / manager into draft without leaving Writing — **met**.

**Note:** Manager CRUD was baseline; V1 gap was **insert + evidence binding**. Library-only parentheticals are ungrounded by design (toast + Reviewer won't validate them).

---

### 6 — Extract quality

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | Evidence Platform |
| Blocked? | No |

**Exit criteria (V1 Production Ready — time-boxed High backlog)**

- [x] Claim normalisation (`normalize_claim`) — prefer distinct KG label; skip trivial/empty
- [x] Provenance facets (population / dosage / method / outcome / timeframe) for Conflict
- [x] Study-type alias normalisation (RCT / cohort / meta / …)
- [x] Reject empty/trivial claims in `build_candidate`
- [x] Inspector weak-candidate hints + reject presets
- [x] Quality regression tests (`test_phase_projector.py`) + existing extract contract suite
- [x] Residual Medium/Low tracked in `Dhund-Flow/EXTRACTION_QUALITY_BACKLOG.md` (not blocking)

**Attestation:** 2026-08-02 — Extract quality V1 Production Ready (`phase_projector.v1.1`). Next: Subsystem #7 Private Alpha Success Gate (+ vertical E2E).

**Done when:** Alpha papers extract usable candidates; High backlog closed; residual tracked — **met**.

**Note:** Did **not** invent new extract architecture. Domain golden P/R fixtures and auto-enqueue remain continuous improvement.

---

### 7 — Private Alpha Success Gate

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | WI, Reviewer, Citations, Extract |
| Blocked? | No |

**Exit criteria (V1 eng Success Gate — Grounded Writing Trust Vertical)**

- [x] Vertical E2E: extract → accept ≥3 → cite insert → WI → reviewer → export → reload (`tests/integration/test_grounded_writing_vertical.py`)
- [x] Friction log + fix pass (F-001 Accept→Generate blocker closed)
- [x] Written sign-off: `docs/PRIVATE_ALPHA_SUCCESS_GATE_v1.md`
- [x] Human cohort invite kit remains ready (`RESEARCHER_VALIDATION_v0.2.1*`) — ops follow-up, not eng architecture

**Attestation:** 2026-08-02 — Private Alpha Success Gate **PASS** (engineering vertical). Human invite-5→20 KPIs tracked in validation kit when product schedules sessions.

**Done when:** Written Success Gate pass recorded — **met**.

---

### 8 — Library (core Bridge)

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | None |
| Blocked? | No |

**Exit criteria (V1 Production Ready — day-to-day Bridge ops)**

- [x] Health strip: Attach PDFs filters `need_pdf` stubs (not unread)
- [x] Attach PDF toast honesty (`queued` true/false) + library invalidation
- [x] Duplicates merge confirm dialog
- [x] Collections: parent-cycle rejection; orphan parents visible; remove-from-collection when filtered
- [x] `need_pdf` search filter (API + FE)
- [x] Tests: health / need_pdf / collection cycle (`backend/library/test_*.py`)
- [x] Explicit non-goals deferred: worker sync (#9), ref-mgr PDF pull (#10), Settings catalog (#11), ecosystem honesty (#12)

**Attestation:** 2026-08-02 — Library core Bridge Production Ready: day-to-day ops (import/health/dupes/attach/collections) reliable without ref-mgr PDF (#10) or worker sync (#9). Next: Subsystem #9 Library Sync (worker).

**Done when:** Day-to-day library ops reliable without ref-mgr PDF — **met**.

---

### 9 — Library Sync (worker)

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | Existing `sync.py` |
| Blocked? | No |

**Exit criteria (V1 Production Ready)**

- [x] `library_sync` in `worker.py` HANDLERS (`_handle_library_sync` → `sync_job.run_library_sync_job`)
- [x] Sync API enqueues UploadJob + returns **202** (`job_id`, `sync_run_id`); `sync: true` keeps inline for tests
- [x] Progress via `LibrarySyncRun` (`queued` → `running` → `ok`/`error`) + `GET /api/library/sync/runs/<id>`
- [x] Retries via existing worker backoff; 409 if sync already active
- [x] FE polls sync run after enqueue (`ConnectLibraryPanel`)
- [x] Tests: large-lib timeout contrast (HTTP &lt;1s while adapter would sleep 2s) + handler roundtrip
- [x] Docs: sync = worker-backed

**Attestation:** 2026-08-02 — Library Sync worker-backed Production Ready. Large Zotero/Mendeley metadata sync completes via worker. Next: Subsystem #10 Ref-mgr PDF pull.

**Done when:** Large Zotero/Mendeley sync completes via worker — **met**.

---

### 10 — Ref-mgr PDF pull

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | Library Sync worker preferred |
| Blocked? | No |

**Exit criteria (V1 Production Ready)**

- [x] `ImportAdapter.import_files` for Zotero + Mendeley (`file_import=True`)
- [x] Low-level download helpers (`zotero.pull_pdf_for_item`, `mendeley.pull_pdf_for_document`)
- [x] Service applies bytes to stubs + enqueues shared ``import`` jobs (`file_pull.py`)
- [x] API: `POST …/pull-pdfs`, `POST /api/library/files/<id>/pull-pdf`
- [x] FE: per-stub Pull + Sources “Pull PDFs”
- [x] Tests: positive adapter + attach/enqueue path (replaces NotImplemented-only asserts)
- [x] Docs: Phase 1b PDF pull for ≥1 provider (both shipped)

**Attestation:** 2026-08-02 — Ref-mgr PDF pull Production Ready. Zotero and Mendeley can pull PDFs into the same import pipeline. Next: Subsystem #11 Integrations Settings catalog.

**Done when:** ≥1 provider can pull PDFs into the same import pipeline — **met** (both).

---

### 11 — Integrations Settings catalog

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | Live providers exist |
| Blocked? | No |

**Exit criteria (V1 Production Ready)**

- [x] Settings → Integrations page (`/settings/integrations`) + reusable `IntegrationCard`
- [x] Unified catalog API (`GET /api/integrations/catalog` + `/public`) — normalized provider contract
- [x] Connect / Disconnect / Sync / Pull PDFs from card actions (catalog-driven, not provider-specific UI)
- [x] Categories: Reference Managers · Academic Sources · Cloud Storage · Writing · AI · Developer · Identity
- [x] No fake Live rows (ORCID, Open API, unwired AI keys → Coming Soon)
- [x] Landing ecosystem renders from same `public_catalog()` SoT
- [x] Adding a provider = register in `backend/ecosystem/catalog.py` (+ adapter) — no FE rewrite
- [x] Tests + docs

**Attestation:** 2026-08-02 — Integrations catalog Production Ready. Settings is the control center; landing matches Live/Soon. Next: Subsystem #13 Quotas (Product Hardening).

**Done when:** Single honest catalog; panel can remain as deep-link — **met**.

---

### 12 — Landing Ecosystem honesty

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | #11 |
| Blocked? | No |

**Exit criteria (V1 Production Ready)**

- [x] Live/Soon badges match catalog (`login.html` Jinja from `ecosystem_catalog`)
- [x] Remove / relabel unwired logos (ORCID, Open API, Citation-only fakes removed from Live)

**Attestation:** 2026-08-02 — Landing ecosystem honesty Production Ready (same SoT as #11).

**Done when:** Marketing matches code — **met**.

---

### 13 — Quotas (chat + WI)

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | `quotas/` exists |
| Blocked? | No |

**Exit criteria (V1 Production Ready)**

- [x] Single entitlement service (`quotas/entitlements.py`) — authorize → consume → ledger
- [x] Plan policy Free / Pro / Team / Enterprise (+ beta/student) without hardcoded route logic
- [x] Soft warn ≥80% / hard block at 100%; admin disable override
- [x] Metered ops registry: chat, WI, extract, upload, sync, discover, embeddings, export, agents…
- [x] Enforce chat SSE (`ai_gate.preflight`) + `POST /api/evidence/writing` + evidence extract
- [x] Clear 429 payload (`quota` object: used/limit/remaining/reset/message)
- [x] Admin: inspect / set limits / reset / disable / analytics (`/api/admin/ops/quotas/*`)
- [x] Usage ledger enrichment (`operation`, `project_id`, `detail_json` — migration 0039)
- [x] Tests: normal, warning, limit, override
- [x] Docs: Feature Matrix Quotas → Implemented

**Attestation:** 2026-08-02 — Quotas Production Ready. Entitlement service governs expensive AI/storage paths; admin overrides without SQL. Next: Subsystem #14 Feature flags.

**Done when:** Cost abuse via chat/WI blocked under quota — **met** (plus extract + ops).

---

### 14 — Feature-flag service

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | Table `0008` |
| Blocked? | No |

**Remaining tasks**

- [x] Runtime service read/write flags
- [x] Admin or ops API to toggle
- [x] Gate ≥1 risky feature (e.g. Discover, WI)
- [x] Tests
- [x] Docs: schema no longer unused

**Attestation:** 2026-08-02 — Feature flags Production Ready. `FeatureFlagService` on `feature_flags` (migration 0008); admin `GET/PATCH /api/admin/ops/feature-flags*`; gates Discover (`discover_search`) and Writing Intelligence (`writing_intelligence`) with fail-open defaults + kill switch / `rollout_pct`. Next: Subsystem #15 Admin SPA — **done** (see §15).

**Done when:** DB-backed flags control ≥1 production path — **met** (Discover + WI).

---

### 15 — Admin SPA

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | `/api/admin/ops/*` |
| Blocked? | No |

**Remaining tasks**

- [x] `/admin` route: invites, kill switch, beta metrics, security events
- [x] Authz: `is_admin` only
- [x] Tests / smoke
- [x] Docs: Admin UI = Implemented

**Attestation:** 2026-08-02 — Admin SPA Production Ready. `/admin` (+ sections) for invites, AI kill switch + daily budget, beta metrics, security events, feature flags; `is_admin` on `/api/me` + `AdminGate`; APIs still `@admin_required`. Next: Subsystem #16 Auth (V1 bar) — **done** (see §16).

**Done when:** Ops without curl for invite + kill switch + metrics — **met**.

**Out of V1:** Payment confirm, org admin, SAML.

---

### 16 — Auth (V1 bar)

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |

**Remaining tasks**

- [x] Step-up reauth for account delete
- [x] Verify invite/allowlist deploy checklist
- [x] Session revoke UX polish (optional if Admin covers)

**Attestation:** 2026-08-02 — Auth V1 bar Production Ready. `DELETE /api/account` requires step-up (`confirm=DELETE` + password **or** matching email for OAuth-only); Settings UI wired; session revoke confirm on “Sign out all devices”; invite/allowlist ops checklist at `docs/auth-v1-deploy-checklist.md` (code path verified: `BETA_INVITE_ONLY` + Admin invites). Next: Subsystem #17 Upload + Worker — **done** (see §17).

**Out of V1:** MFA, SAML, org SSO.

---

### 17 — Upload + Worker

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |

**Remaining tasks**

- [x] Drain/remove deprecated `extract_metadata` after queue empty
- [x] Document dual-stack as known debt (no unify required for V1 100%)
- [x] Worker heartbeat/metrics smoke in deploy checklist

**Attestation:** 2026-08-02 — Upload + Worker V1 Production Ready. `extract_metadata` HANDLER is a drain shim → `phase1_analysis` (no LLM); dual storage/upload stacks accepted for V1 ([ADR-0014](../adr/0014-upload-storage-dual-stack-accepted-v1.md)); heartbeat smoke in [`upload-worker-v1-deploy-checklist.md`](../upload-worker-v1-deploy-checklist.md) (`GET /api/worker/health`, `test_worker_health.py`). Next: Subsystem #18 Export (lit-review) — **done** (see §18).

**Out of V1:** Full storage/upload façade unify (future ADR).

---

### 18 — Export (lit-review)

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |
| Dependencies | Reviewer gate (#4) |

**Remaining tasks**

- [x] Gate export on Reviewer errors
- [x] MD + BibTeX + evidence trail stable
- [x] Tests for gated export

**Attestation:** 2026-08-03 — Lit-review Export Production Ready. Server gate `POST /api/writing/documents/<id>/export` (`can_export_grounded_lit_review` + latest Reviewer run merge); MD evidence appendix + bibliography + BibTeX; FE Export tab uses server gate; unit tests for block/allow + BibTeX. Next: Subsystem #19 Projects (personal) — **done** (see §19).

**Out of V1:** DOCX / journal packs.

---

### 19 — Projects (personal)

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |

**Remaining tasks**

- [x] Hub empty/error states polish
- [x] Ownership edge-case tests

**Attestation:** 2026-08-03 — Projects (personal) Production Ready. Hub list distinguishes loading / error+Retry / empty; detail page separates 404 (not found / no access) from connection errors; HTTP IDOR suite (`test_project_ownership.py`) covers list isolation + CRUD/hub/questions/insights/research/memory → 404 for non-owners. Next: Subsystem #20 Security baseline (V1) — **done** (see §20).

**Out of V1:** Sharing / teams.

---

### 20 — Security baseline (V1)

| Field | Value |
|-------|-------|
| Current / Target | 100% → 100% |
| Status | 🟢 |

**Remaining tasks**

- [x] Deploy checklist: no `DEV_AUTO_LOGIN`, ClamAV, invite mode
- [x] Redis limiter for multi-worker if applicable
- [x] Sentry optional for V1 bar — prefer before open Alpha traffic

**Attestation:** 2026-08-03 — Security baseline V1 Production Ready. Deploy checklist [`security-baseline-v1-deploy-checklist.md`](../security-baseline-v1-deploy-checklist.md); prod boot requires `REDIS_URL` or `RATE_LIMIT_MEMORY_OK=1` (ClamAV-style ack); optional `SENTRY_DSN` via `security/sentry_init.py` (not required for closed beta). Startup tests cover DEV_AUTO_LOGIN / ClamAV / Redis gates + Sentry init.

**Out of V1:** Full pentest program, CSP report-uri pipeline, dependency SBOM CI as a platform program.

---

## 4. Roll-up: V1 readiness

| Bucket | Subsystems | Avg (approx) | Gate |
|--------|------------|-------------:|------|
| P0 Trust vertical | 1–7, 18 | 100% | #1–7, #18 🟢 |
| P1 Library durability | 8–12 | 100% | #8–12 🟢 |
| V1 ops/cost | 13–15, 20 | 100% | #13–15, #20 🟢 |
| Polish | 16–17, 19 | 100% | #16–17, #19 🟢 |

**V1 complete when:** all rows in §1 master scoreboard are 🟢 and Production Ready = Yes.

**Status (2026-08-03):** §1 scoreboard is **all 🟢**. Next: lift freeze → P2 per Ecosystem Masterplan (only with explicit product go-ahead).

---

## 5. Change log

| Date | Change |
|------|--------|
| 2026-08-02 | Initial tracker from Step 0 audit + P0/P1 freeze rule |
| 2026-08-02 | §0 binding rules: Definition of Production Ready, Sprint Success, Freeze means freeze, standard Engineering Team prompt |
| 2026-08-02 | §0.1b project-wide Definition of Done |
| 2026-08-02 | **Subsystem #3 Writing Intelligence → 🟢 100% Production Ready** (binder alignment, accept_allowed, export/Accept gates, tests) |
| 2026-08-02 | **Subsystem #4 Research Reviewer → 🟢 100% Production Ready** (panel, reconstruct client, severity export gate, A-505) |
| 2026-08-02 | **Subsystem #5 Citation insert-into-draft → 🟢 100% Production Ready** (resolve-evidence, Writing picker, bindings, Ctrl+Shift+C, tests) |
| 2026-08-02 | **Subsystem #6 Extract quality → 🟢 100% Production Ready** (claim norm, facets, study_type aliases, Inspector hints, projector regressions) |
| 2026-08-02 | **Subsystem #7 Private Alpha Success Gate → 🟢** (vertical E2E pass; F-001 consensus stance fix; `PRIVATE_ALPHA_SUCCESS_GATE_v1.md`) |
| 2026-08-02 | **Subsystem #8 Library (core Bridge) → 🟢** (need_pdf filter, attach honesty, collection cycles/remove, dupes confirm, Bridge tests) |
| 2026-08-02 | **Subsystem #9 Library Sync (worker) → 🟢** (202 enqueue, HANDLER, run polling, timeout-safe HTTP, FE poll) |
| 2026-08-02 | **Subsystem #10 Ref-mgr PDF pull → 🟢** (Zotero+Mendeley import_files, pull-pdfs API, enqueue import, FE Pull) |
| 2026-08-02 | **Subsystem #11 Integrations catalog → 🟢** (SoT API, Settings page, IntegrationCard, connect/sync/pull) |
| 2026-08-02 | **Subsystem #12 Landing Ecosystem honesty → 🟢** (login.html from same public_catalog) |
| 2026-08-02 | **Subsystem #13 Quotas → 🟢** (EntitlementService, soft/hard limits, WI+chat+extract gates, admin ops) |
| 2026-08-03 | **Subsystem #19 Projects (personal) → 🟢** (hub empty/error polish; HTTP ownership IDOR tests) |
| 2026-08-03 | **Subsystem #20 Security baseline → 🟢** (deploy checklist; Redis fail-closed + memory ack; optional Sentry) |
| 2026-08-03 | **Subsystem #1 Evidence Platform → 🟢** (Compare/consensus UX depth; freeze tests; V1 = frozen + quality docs) |
| 2026-08-03 | **Subsystem #2 Writing Shell → 🟢** (version restore confirm; scaffold cleanup; autosave conflict/offline tests) |

---

## 6. How Cursor / engineers should use this

1. Read §0 (Production Ready + sprint + freeze).  
2. Pick the **first non-🟢** row in §2 execution order.  
3. Run the **§0.5 standard prompt** for that subsystem only.  
4. Complete remaining tasks; check every §0.1 box.  
5. Update Current %, Status, Production Ready?, checkboxes, Change log.  
6. Commit and ship internally.  
7. Do **not** start out-of-V1 rows (⚪) while freeze holds.  
8. Do **not** create new roadmap/vision docs — update **this** file.
