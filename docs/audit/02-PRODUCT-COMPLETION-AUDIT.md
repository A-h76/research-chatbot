# Product Completion Audit

**Product:** Dhund Research OS  
**Audit date:** 2026-08-02  
**Purpose:** What V1 shipped, what was paused/MVP’d, feature recovery inventory, frontend↔backend mismatches.

**Related:** [01-CURRENT-ARCHITECTURE-AUDIT.md](01-CURRENT-ARCHITECTURE-AUDIT.md) · [03-TECHNICAL-DEBT-REPORT.md](03-TECHNICAL-DEBT-REPORT.md) · [04-RESEARCH-OS-ROADMAP.md](04-RESEARCH-OS-ROADMAP.md)

---

## 1. Honest product label

**Today:** Closed-beta **personal** Research OS — strong Evidence Platform + library/upload + writing shell; weak/absent orgs, billing, in-app notifications, admin UI, product automation.

**Not today:** Multi-tenant SaaS, collaborative lab OS, or a ChatGPT clone with research stickers.

---

## 2. What Version 1 intentionally shipped

| Capability | Evidence |
|------------|----------|
| Invite-gated auth (Google, magic link, password) + JWT bridge | `auth/`, `security/ops/` |
| Projects hub (personal) | `backend/projects/` |
| Dual upload → shared worker pipeline | `backend/upload/`, `worker.py` |
| Library Bridge (BibTeX/RIS, Zotero/Mendeley metadata sync) | `backend/library/` |
| Discover via OpenAlex | `discover_routes.py` |
| Phase 1 analysis 1.1–1.7 + paper workspace | `backend/analysis_pipeline/` |
| Evidence Platform + RI stages (frozen) | `backend/evidence/`, contracts |
| Writing Studio shell (autosave, versions) | `backend/writing/` |
| Grounded Writing Intelligence path | `POST /api/evidence/writing` |
| Citations manager + BibTeX export | `citation_routes.py` |
| Streaming chat (tool, not OS spine) | `server.py` `/api/chat` |
| Security baseline + ops admin APIs | `docs/SECURITY_BASELINE_v1.0.md` |
| Marketing landing (Jinja) | `templates/login.html` |

---

## 3. What was paused, MVP’d, or deferred

| Item | Why paused | Recovery priority |
|------|------------|-------------------|
| Orgs / teams / shared projects | Personal beta first | After public SaaS bet |
| Billing / entitlements | Soft-launch parallel (SaaS-PK) | Before open signup |
| Feature-flag DB service | Env flags enough for beta | Before risky rollouts |
| KG v2 / Neo4j / Novelty | Track 2 usage-gated | After alpha demand |
| Research Session Engine | ADR-0013: do not implement yet | After lit-review vertical |
| In-app notifications | Email enough for auth | Medium |
| Admin SPA | Curl/API ops for beta | Medium |
| PDF auto-pull from Zotero/Mendeley | Phase 1b stub | High (library durability) |
| Worker-backed library sync | In-request sync shipped first | High |
| PubMed / arXiv / Europe PMC APIs | Discover via OpenAlex | High (discovery) |
| Cloud storage watch (Drive/Dropbox) | Not started | After core finish |
| Writing bi-sync Docs/Notion | Export-first | Phase 2 integrations |
| Chat as primary research spine | Demoted to tool | Keep demoted; build Evidence Assistant |
| DocumentBlock / comments / track-changes | Week-1 future entities | After insert-citations |
| DOCX / journal publication packs | Explicit non-goal until alpha | Later |
| Research Framing workspace (Target M5) | Reordered behind Evidence/RI | Medium–Low |
| External webhooks / Zapier / MCP product | First-party only | After alpha |
| OCR / scanned PDF indexing | Text PDFs prioritized | Medium (quality) |

---

## 4. Feature Recovery Report

Effort: **S** (<1 week) · **M** (1–2 weeks) · **L** (2–4 weeks) · **XL** (multi-sprint / ADR).

| Feature | Intended purpose | Current implementation | Missing engineering | Effort |
|---------|------------------|------------------------|---------------------|--------|
| Reviewer FE + export gate | Trust critique before publish | BE engine + persistence; issues in Verify/strip | Accordion, `reviewer-runs` client, gate export on severity=error | M |
| Citation insert-into-draft | Cite while writing (Target M4) | Citations manager + WI `[#id]` binder | Editor picker + span/binding APIs | L |
| WI binder quality | Every claim grounded | Binder module + Verify UX | Quality loops; fewer heuristic falls | L |
| Extract quality | Better EvidenceObjects | Extract pipeline + backlog | Assessor polish (`EXTRACTION_QUALITY_BACKLOG`) | L |
| Library PDF pull | True ref-mgr OS | Meta sync; `file_import=False` | `ImportAdapter.import_files` + attach pipeline | L |
| Worker `library_sync` | Durable sync | Sync HTTP in-request | HANDLER + progress + retries | M |
| Settings Integrations catalog | Honest connect hub | `ConnectLibraryPanel` | Settings page + status API facade | M |
| PubMed / arXiv clients | Real biomedical/preprint discovery | UI hints / OpenAlex only | `backend/scholarly/` modules + Discover UI | M |
| Google Drive folder watch | PDF inflow without manual upload | None | OAuth + adapter + worker import | L |
| Feature-flag service | Safe rollout / kill expensive features | Empty `feature_flags` table | Service + admin + FE gating | M |
| Chat / WI quota gate | Cost control | Storage + partial tokens + AI kill switch | Enforce on SSE chat + WI | M |
| Evidence Discovery UX | Search → cards → consensus → Writing | RI APIs on Analysis page | First-class Discovery flow (Milestone 2) | L |
| Evidence-first Assistant | Answers cite EvidenceObject IDs | Chat + paper chat; Stage 1 off | Citation-required mode + UX refuse | L |
| Admin SPA | Ops without curl | `/api/admin/ops/*` | Invites, kill switch, metrics UI | L |
| Billing / entitlements | Public launch monetization | Design docs only | Plans, checkout (JazzCash B0), enforce caps | XL |
| Teams / collaboration | Lab workflows | None | AuthZ ADR + sharing + comments | XL |
| Notifications center | Job/sync awareness | Transactional email | Table + bell UI + prefs | L |
| Research Session Engine | Durable research hub | ADR-0013 only | Full build (do not start early) | XL |
| DOCX / journal export | Publication | MD/BibTeX | Packs + ExportJob | L |
| External webhooks | Automation | Internal outbox only | Signed delivery + subscriptions | L |
| OCR / scanned index | Scanned paper readiness | Quality detect; chat vision | OCR job + embed path | L |
| Notebook / PDF annotations | Mark-up papers in-product | Notes CRUD | Annotation layer + viewer | XL |
| Dual-stack unification | One storage/upload/AI story | Dual facades by design | Incremental ADR façade | L |
| Prompt Engine chat unify | One AI stack | Parallel Responses path | Finish migration (ADR-0012 deferred work) | L |
| Landing Trust page | Security/trust marketing | `/trust` absent (SPA catch-all) | Static/Jinja trust page | S |
| Marketing pricing honesty | Convert without oversell | Placeholder pricing | Tie to live entitlements | S (+ L with billing) |

---

## 5. Frontend vs backend mismatch map

| Surface | Backend | Frontend | Verdict |
|---------|---------|----------|---------|
| Admin ops | ✅ `/api/admin/ops/*` | ✅ `/admin` SPA (#15) | Done |
| Reviewer runs | ✅ reconstruct APIs | Thin / unused | Missing UI |
| Evidence compare/consensus | ✅ APIs | Thin Compare page | Partial UI |
| Feature flags table | Schema | ❌ | Missing service + UI |
| Billing | ❌ | ❌ | Missing both |
| `/trust` | — | ❌ | Missing marketing |
| Library sync | ✅ HTTP | ✅ panel | Works; needs worker |
| Integrations Settings | Partial APIs | ❌ dedicated page | Missing UI |
| Writing shell | ✅ | ✅ | Aligned |
| Grounded WI | ✅ | ✅ desk | Aligned; polish gap |
| Citations CRUD | ✅ | ✅ manager | Aligned; insert gap |
| Notes | ✅ | ✅ | Aligned |
| Notifications | Email only | ❌ center | Missing product |
| Orgs / teams | ❌ | ❌ | Deferred |
| Public developer API | ❌ | ❌ | Deferred |

### SPA routes present vs absent

**Present:** home, chat, projects, library, papers, compare, citations, notes, memory, search, writing, settings, legal/support.

**Absent:** `/billing`, `/orgs`, `/teams`, `/notifications`, developer portal. `/admin` shipped (#15).

---

## 6. Writing Studio completion (product view)

| Layer | Designed | Shipped | Gap to vision |
|-------|----------|---------|---------------|
| Shell | Full | ~90% | Blocks/comments |
| Grounded WI eng | Full lit-review vertical | ~82% | Binder quality + alpha gate |
| Reviewer product | Compiler-shaped critique | BE ~85% · FE ~40% | FE + export gate |
| Citations in draft | Target M4 | ~0% insert | Major |
| Publication | Packs | MD only | Deferred OK |
| Collab writing | Comments | 0% | Deferred |

**Required to reach Research OS writing vision (not new greenfield):**

1. Finish binder + Verify quality  
2. Ship Reviewer FE + export gate  
3. Citation insert-into-draft  
4. Close Private Alpha Success Gate (unassisted researcher)  
5. Only then: Discovery UX polish, DOCX packs, framing workspace  

---

## 7. Pipeline completion % (product)

| Link | % | Status |
|------|--:|--------|
| Import | 90 | Production-ready for beta |
| Metadata | 75 | OCR / enrich gaps |
| Knowledge Graph | 70 | Dual surfaces; no v2 |
| Evidence | 95 | Frozen; quality backlog |
| Grounded AI | 80 | Chat bypass risk |
| Writing | 78 | Trust path incomplete |
| Citations | 55 | Insert missing |
| Export | 70 | Lit-review practical |
| Collaboration | 5 | Deferred |
| Automation | 15–40 | Jobs ≠ product automation |
| **Lit-review vertical overall** | **~75** | Eng high; validation open |
| **Full Target.md Research OS vision** | **~55** | SaaS/collab/publication out |

---

## 8. Completion verdict

| Question | Answer |
|----------|--------|
| Ship more integrations first? | **No** — finish unfinished core first |
| Biggest unfinished core? | Grounded lit-review **trust** path (Reviewer FE, cite insert, binder, alpha) |
| Biggest false-promise risk? | Ecosystem logos / billing / collab not wired |
| Rewrite Evidence or Writing? | **No** — finish |
| Greenfield Integration Platform? | **No** — extend adapters / scholarly / worker |

See [04-RESEARCH-OS-ROADMAP.md](04-RESEARCH-OS-ROADMAP.md) for prioritized execution order.
