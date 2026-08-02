# Current Architecture Audit

**Product:** Dhund Research OS (formerly ResearchOS / Soro / Personal AI)  
**Audit date:** 2026-08-02  
**Scope:** Full repository — subsystem status, pipeline links, Writing Studio deep dive  
**Stance:** Closed-beta **personal** Research OS. Do not assume the current UI is the full intended product.

**Related:** [02-PRODUCT-COMPLETION-AUDIT.md](02-PRODUCT-COMPLETION-AUDIT.md) · [03-TECHNICAL-DEBT-REPORT.md](03-TECHNICAL-DEBT-REPORT.md) · [04-RESEARCH-OS-ROADMAP.md](04-RESEARCH-OS-ROADMAP.md)

**Sources:** live code (`backend/`, `frontend/`, `worker.py`, `auth/`, `security/`), freezes (`docs/contracts/RI-v3.0-COMPLETE-FREEZE.md`, `Dhund-Flow/PLATFORM_FREEZE_v1.0.md`), `Dhund-Flow/FEATURE_MATRIX.md`, `Target.md`, ADRs, EPICs.

---

## 1. System map

```text
Landing (Jinja) ──► Auth (Google / magic / password / JWT)
                         │
                         ▼
                   React SPA
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Upload         Library        Evidence
          │              │              │
          └──────► Worker HANDLERS ◄────┘
                     │
         import → phase1 → paper_analysis
                     │
              evidence_extract (optional)
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
     Writing Shell  WI      Chat SSE
          │          │          │
          └──── ModelRouter / Gateway / Registry (partial unify)
```

**Data plane:** Postgres (source of truth) · dual storage facades (`storage/` + `backend/storage/`) · Redis optional (job status cache, rate limits).

---

## 2. Subsystem scoreboard

Status vocabulary: **Production Ready** · **MVP** · **Incomplete** · **Prototype** · **Needs Rewrite** · **Abandoned** · **Deferred**.

Debt tags: Missing UI / Backend / Database / API / Workers / Tests · Performance · Security · Technical Debt.

| Subsystem | Status | ~% | Missing / debt | Notes |
|-----------|--------|---:|----------------|-------|
| Authentication | Production Ready | 100 | MFA / SAML (out of V1) | Session + JWT `sv`; step-up delete; invite/allowlist checklist |
| User onboarding | MVP | 78 | Guided first-upload tour; Prompt Engine consumption of prefs | Wizard + `/api/onboarding/complete` |
| Organizations | Deferred | 0 | Everything | Single `user_id` ownership |
| Projects | MVP | 85 | Sharing / roles | Hub, memory, research, notes |
| Research Workspace (Papers) | MVP | 80 | Tab polish; Evidence naming collision | Phase 1 tabs live |
| Knowledge Graph (paper 1.7) | MVP | 70 | Product polish | In-process JSON; no Neo4j |
| Knowledge Graph (project RI-005) | MVP | 80 | Writing-first Discovery UX | `/api/projects/<id>/evidence/graph` |
| KG v2 / Novelty | Deferred | 0 | Track 2 | Usage-gated; do not start |
| Evidence Engine / Layer | Production Ready | 95 | Extract quality backlog; Compare UX depth | Frozen `v0.2.0-rc1` / RI contracts |
| Document Import / Uploads | Production Ready* | 100 | Facade unify (post-V1 ADR) | *Dual stack accepted V1 — ADR-0014 |
| PDF Processing | MVP | 72 | OCR job; index scanned PDFs | PyMuPDF; scanned → chat vision only |
| Citation Engine | MVP | 55 | Insert-into-draft | Manager + WI binder + BibTeX |
| Reference Manager (Zotero/Mendeley) | MVP | 70 | `import_files` PDF pull; Settings catalog | Meta sync live; `file_import=False` |
| Writing Studio Shell | Production Ready | 90 | Block/comment models | Autosave, versions, lifecycle |
| Writing Intelligence | MVP | 82 | Binder quality; alpha E2E validation | `POST /api/evidence/writing` |
| Review Builder (Research Reviewer) | Incomplete | 65 | Reviewer FE (B-511–514); export gate | Backend + persistence done |
| Notebook | Incomplete | 5 | Entire surface | Notes ≠ notebook |
| Annotations | Incomplete | 30 | PDF/page layer | Design maps to notes `kind=annotation` |
| AI Chat | Production Ready (as tool) | 80 | Quota gate; Evidence-mandated answers | Demoted as OS spine |
| Model Router / Registry / Gateway | MVP | 85 | Dual invoke with chat Responses | Frozen Gateway v1.0 for WI path |
| Prompt Engine | MVP | 60 | Chat migration; Paper Chat Stage 1 off | Analysis/research wired |
| Search (semantic + library) | MVP | 68 | ANN; `SearchIndex` decision; dual APIs | O(n) cosine |
| Discover (OpenAlex) | MVP | 75 | PubMed/arXiv APIs | Stubs + DOI dedup |
| Library / Collections | Production Ready / MVP | 86 / 80 | Collection-scoped research polish | Bridge 1a–1c shipped |
| Uploads (bulk / presign) | Production Ready | 82 | Presign not primary SPA path | Shared `UploadJob` + outbox |
| Export | MVP | 100 | DOCX/journal packs (out of V1) | Grounded MD + BibTeX + server Reviewer gate (#18) |
| Integrations catalog UI | Incomplete | 20 | Settings Integrations page | `ConnectLibraryPanel` only |
| Automation (product) | Prototype | 15 | User rules, watchers, Zapier | Worker jobs ≠ product automation |
| Background Workers | Production Ready | 100 | Sentry optional | Postgres SKIP LOCKED; `extract_metadata` drain shim (#17) |
| Notifications (in-app) | Incomplete | 20 | Center + prefs | Transactional email only |
| Settings | MVP | 85 | Billing / team / notifications sections | Personal prefs strong |
| Billing / payments | Incomplete | 0 | Plans, checkout, entitlements | SaaS-PK docs only |
| Usage Limits / Quotas | Incomplete | 60 | Chat/WI full gating; plan caps | Storage + token paths partial |
| Team Collaboration | Deferred | 5 | All | Explicit non-goal for V1 |
| Permissions / RBAC | MVP | 55 | Org roles; share links | Ownership + `is_admin` |
| Admin | Incomplete | 68 | Admin SPA | `/api/admin/ops/*` live |
| Landing / Marketing | MVP | 72 | Trust page; pricing honesty | Jinja mega-landing |
| Developer APIs (public) | Incomplete | 10 | Keys, versioning, docs portal | First-party REST only |
| Observability | MVP | 60 | Sentry; product analytics UI | Prometheus + JSON logs + workflow events |
| Security baseline | Production Ready | 90 | Redis limiter multi-worker; open-signup risk | SECURITY_BASELINE v1.0 |
| Infrastructure (Render/Postgres) | MVP | 75 | Horizontal worker story | Ephemeral FS; R2/local storage |
| Feature-flag service | Abandoned (as product) | 15 | Runtime service | Table `0008` unused; env flags only |
| Memory | MVP | 55 | Embedding rank | Token-overlap TODO in `memory_engine.py` |

---

## 3. Research pipeline — missing links

```text
Import Paper
    ✅  upload + library bridge + discover stubs
        ↓
Metadata Extraction
    ✅ / 🟡  Phase1 + Crossref; DOI enrich uneven; OCR gap
        ↓
Knowledge Graph
    🟡  per-doc 1.7 + project RI-005; no KG v2 / Neo4j
        ↓
Evidence Extraction
    ✅  extract job + review UI; quality backlog continuous
        ↓
Grounded AI
    🟡  WI + Evidence Query stages; chat can bypass Evidence
        ↓
Writing Studio
    🟡  shell ✅ · WI partial · Reviewer FE thin
        ↓
Citation Engine
    🟡  manager ✅ · insert-into-draft ❌
        ↓
Export
    🟡  MD/BibTeX ✅ · DOCX/journal ❌
        ↓
Collaboration
    ❌
        ↓
Automation
    ❌  (telemetry + jobs only)
```

### Thin links to fix first

1. Evidence accept → unassisted lit-review E2E (Private Alpha Success Gate)  
2. Citation insert-into-draft  
3. Reviewer FE + pre-export severity gate  
4. Library sync durability (worker HANDLER) + PDF `import_files`  
5. Chat / WI quota enforcement  

### Worker job inventory (`worker.py`)

| Job | Role | Notes |
|-----|------|-------|
| `import` | Extract → chunk → embed → Crossref → enqueue phase1 | Primary |
| `extract_metadata` | Drain shim → phase1 (#17) | Drop HANDLER when prod pending=0 |
| `phase1_analysis` | AnalysisPipelineService 1.1–1.7 | Primary |
| `paper_analysis` | LLM overview + Phase 1 context | |
| `evidence_extract` | EvidenceObject extraction | |
| `theme_map` | Multi-paper themes | |
| `literature_review` | Lit-review job | |
| `library_sync` | — | **Missing** (sync is in-request today) |

---

## 4. Writing Studio deep dive

### 4.1 Originally designed

| Layer | Intent | Sources |
|-------|--------|---------|
| Shell (M2 / Week 1) | Documents → versions → autosave → audit; no freeform paper writer | `Target.md` M2; `docs/architecture/week1-writing-shell-architecture.md` |
| Extended entities | `DocumentBlock`, citation/evidence links, `CommentThread`, `ChangeProposal` | Week-1 arch (future) |
| Writing Intelligence | Evidence → plan → context → sections → bind → reviewer → metrics | RI-009; EPIC-0004; `backend/evidence/writing/` |
| UI desk | Outline · Manuscript · Evidence; Verify; Confidence; Export | EPIC-0004 B-411…416 |
| Explicit non-goals (then) | DOCX/journal packs; parallel ungrounded generate | EPIC-0004 |

### 4.2 What currently exists

| Layer | Path | ~% |
|-------|------|---:|
| Writing Shell BE | `backend/writing/` (document/autosave/version routes) | 90 |
| Writing Intelligence BE | `backend/evidence/writing/*`, `writing_intelligence.py`, `POST /api/evidence/writing` | 82–90 |
| Reviewer BE + persistence | `writing/reviewer.py`, migration `0035` | 85 |
| Frontend desk | `frontend/src/features/writing/`, `useGroundedWriting.ts` | 75 |
| Style-only assistant | `backend/writing/api/assistant_routes.py` `/api/writing` | Kept, labeled non-grounded |

### 4.3 Removed / MVP’d / deferred

| Item | Disposition |
|------|-------------|
| Freeform “write my paper” AI | Out of scope for shell |
| DocumentBlock / comments / track-changes | Designed, not built |
| In-editor citation picker (Target M4) | Manager exists; insert Planned |
| DOCX / journal packs | Deferred |
| Research Framing workspace (Target M5) | Not shipped |
| Reviewer FE B-511–514 | Persistence done; FE open |
| Full Target.md ADR list | Superseded by Evidence/RI freezes |
| Chat as Research OS answer spine | Intentionally demoted |

### 4.4 Backend vs frontend gaps

| Capability | Backend | Frontend | Gap |
|------------|---------|----------|-----|
| Document shell | ✅ | ✅ | Thin store; rich-text `editor_kind` unused |
| Grounded generate | ✅ | ✅ | Product validation, not missing API |
| Bindings | ✅ | ✅ persist on accept | Span-level anchors weaker than designed blocks |
| Reviewer runs | ✅ reconstruct APIs | Thin / unused client | **Major** |
| Export grounded MD/Bib | ✅ + FE | ✅ Export tab | Journal packs missing |
| Style transforms | ✅ | ✅ buttons | Can confuse “research-backed” promise |
| Citation insert | ❌ Target M4 | ❌ | **Major** |
| Collaboration comments | ❌ | ❌ | Deferred |

**Writing Studio overall:** ~78% (shell high; WI eng high; Target M4/M5/M6 product incomplete).

**Do not rewrite** shell tables, WI module shape, or EvidenceObject contracts — finish quality.

---

## 5. Dual-stack architecture (intentional debt)

| Concern | Stack A | Stack B |
|---------|---------|---------|
| Storage | `storage/` (session upload, GC) | `backend/storage/` (JWT documents) |
| Upload APIs | `POST /api/files` session | `POST /api/documents/upload`, bulk, presign JWT |
| Search | `POST /api/search` session | `GET /api/documents/search`, `POST /api/rag` JWT |
| AI invoke | `server.py` OpenAI Responses (chat) | ModelRegistry Completions (WI / Prompt Engine) |
| Cost | Legacy usage ledger | Prompt Engine / registry cost ledger |

Both upload paths enqueue the same `UploadJob` + `OutboxEvent`. Unify requires ADR — not a drive-by rewrite.

---

## 6. Security & performance snapshot

| Area | Assessment |
|------|------------|
| Security baseline | Strong for closed beta (CSP, invite gate, sealed OAuth tokens, ClamAV when required) |
| Open signup + empty allowlist | Cost-abuse risk on public deploy |
| Account delete | Step-up reauth (#16) |
| RAG retrieval | O(n) cosine over JSON embeddings — fine for beta, not 10k-doc scale |
| Library sync | In-request — timeout risk for large Zotero libraries |
| Worker | Postgres required; SQLite = silent no-processing |
| Observability | No Sentry / paging |

---

## 7. Freeze / do-not-rewrite boundaries

- EvidenceObject / RI stage APIs / Evidence Query contract (`docs/contracts/`)  
- Writing shell schema (migrations `0031`–`0032`)  
- AI Gateway policy shape for WI  
- Postgres SKIP LOCKED worker + `HANDLERS` extension pattern  
- `ImportAdapter` extension (no greenfield `backend/integrations/` package)  
- Constitution: never `import server`; no wholesale rewrites without ADR  

---

## 8. Verdict

Dhund is **not** “almost done.” Evidence Platform (~95%) and Writing Shell (~90%) are the strongest cores. The unfinished Research OS spine is the **grounded lit-review trust path** (Reviewer FE, citation insert, binder quality, alpha validation) plus **library durability** (worker sync, PDF pull). Orgs, billing, notifications, and automation are largely absent by design for V1 — recover them only after the core vertical works unassisted.
