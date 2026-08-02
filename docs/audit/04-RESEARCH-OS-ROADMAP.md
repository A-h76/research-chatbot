# Research OS Roadmap

**Product:** Dhund Research OS  
**Audit date:** 2026-08-02  
**Principle:** Finish unfinished **core** systems before major new capabilities (Drive, 50 integrations, teams, billing depth).

**Related:** [01-CURRENT-ARCHITECTURE-AUDIT.md](01-CURRENT-ARCHITECTURE-AUDIT.md) · [02-PRODUCT-COMPLETION-AUDIT.md](02-PRODUCT-COMPLETION-AUDIT.md) · [03-TECHNICAL-DEBT-REPORT.md](03-TECHNICAL-DEBT-REPORT.md) · **Vision:** [05-RESEARCH-OS-VISION.md](05-RESEARCH-OS-VISION.md)

**Aligned with:** `docs/roadmap/EXECUTION-DUAL-TRACK.md`, `Dhund-Flow/PLATFORM_FREEZE_v1.0.md`, `Dhund-Flow/ENGINEERING_ROADMAP.md`

**Strategic pillars (after P0–P4):** [06 Graph](06-KNOWLEDGE-GRAPH-PRODUCT.md) · [07 Memory](07-RESEARCH-MEMORY.md) · [08 Agents](08-RESEARCH-AGENT-LAYER.md) · [09 Enterprise](09-ENTERPRISE-ROADMAP.md) · [10 Ecosystem](10-RESEARCH-ECOSYSTEM-MASTERPLAN.md)

---

## 1. Goal

Transform the current closed-beta codebase into the **complete Dhund Research OS originally envisioned** — Evidence-grounded import→write→cite→export — without greenfield rewrites and without confusing marketing logos for shipped product.

This document is the **near-term engineering roadmap (P0–P4)**. The enduring product thesis lives in [05-RESEARCH-OS-VISION.md](05-RESEARCH-OS-VISION.md).

```text
P0 Lit-review trust  →  P1 Library durability  →  P2 Discovery & storage
         →  P3 Hardening  →  P4 SaaS / collab / automation
         →  P5 Graph · P6 Memory · P7 Agents  (+ Enterprise E1–E4)
```

---

## 2. Non-goals (until later)

- Greenfield `backend/integrations/` package duplicating tokens/sync  
- Replacing Postgres SKIP LOCKED with Celery  
- Neo4j / KG v2 by default  
- Making freeform Chat the Research OS answer spine  
- Claiming SOC 2 / HIPAA without programs  
- Research Session Engine (ADR-0013) before Alpha validates home surface  
- Public Developer API / Zapier before first-party vertical works  

---

## 3. Phase P0 — Finish Research OS spine (now)

**Outcome:** Unassisted researcher can import papers → extract evidence → generate grounded lit-review → verify → review → export with trust.

| # | Work item | Why | Effort |
|---|-----------|-----|--------|
| P0.1 | Writing Intelligence binder quality + Verify UX polish | Claims must ground | L |
| P0.2 | Research Reviewer FE (EPIC-0005 B-511–514) + export gate on severity=error | Trust before publish | M |
| P0.3 | Citation insert-into-draft (Target M4) | Cite while writing | L |
| P0.4 | Extract quality backlog (top items) | Better EvidenceObjects | L |
| P0.5 | Private Alpha Success Gate — unassisted lit-review validation | Eng ≠ product-done | M |

**Do not rewrite:** EvidenceObject, RI stages, Writing shell tables, WI pipeline module shape.

**Exit criteria:** Researcher completes lit-review flow without engineer help; export blocked when Reviewer severity=error; citations insertable into draft.

---

## 4. Phase P1 — Library durability

**Outcome:** Reference managers and library sync are durable and honest in Settings.

| # | Work item | Why | Effort |
|---|-----------|-----|--------|
| P1.1 | Worker `library_sync` HANDLER | Avoid in-request timeouts | M |
| P1.2 | Zotero/Mendeley `import_files` PDF pull | Meta-only → real OS | L |
| P1.3 | Settings → Integrations catalog (status for live providers) | Honest connect hub | M |
| P1.4 | Align landing Ecosystem Live/Soon badges with truth | No false promises | S |

**Extend only:** `backend/library/adapters/`, `worker.py` HANDLERS, thin Settings facade.

**Exit criteria:** Large library sync completes via worker; at least one provider can attach PDFs; Settings lists Live vs Soon accurately.

---

## 5. Phase P2 — Discovery & storage integrations

**Outcome:** Research sources feed the Knowledge/Evidence loop without a parallel platform.

| # | Work item | Why | Effort |
|---|-----------|-----|--------|
| P2.1 | PubMed (NCBI) scholarly client + Discover UI | Biomedical discovery | M |
| P2.2 | arXiv / Europe PMC clients | Preprints / EU literature | M |
| P2.3 | Google Drive folder watch → worker import | PDF inflow | L |
| P2.4 | Dropbox → OneDrive | Same adapter pattern | L |
| P2.5 | ORCID identity OAuth | Researcher identity | M |

**Rule:** Extend `backend/scholarly/` + `ImportAdapter` + HANDLERS — no duplicate token tables.

**Exit criteria:** At least PubMed + one cloud folder path import into the same `UploadJob` pipeline as native upload.

---

## 6. Phase P3 — Product hardening

**Outcome:** Safe to open traffic and roll features without ops-by-curl.

| # | Work item | Why | Effort |
|---|-----------|-----|--------|
| P3.1 | Feature-flag service on existing `feature_flags` table | Safe rollouts | M |
| P3.2 | Enforce quotas on chat SSE + Writing Intelligence | Cost abuse | M |
| P3.3 | Admin SPA (invites, kill switch, budgets, beta metrics) | Ops UI | L |
| P3.4 | Sentry + funnel / workflow analytics dashboards | Paging + funnel | M |
| P3.5 | ADR: storage/upload façade + thin Responses executor | Dual-stack without rewrite | L |
| P3.6 | Decide `SearchIndex` / `ImportSession` — wire or drop | Schema honesty | S–M |
| P3.7 | OCR job + embed scanned PDFs (if alpha demand) | Scanned readiness | L |

**Exit criteria:** Kill switch + invites from UI; chat/WI respect quotas; errors page to Sentry; dual-stack ADR accepted.

---

## 7. Phase P4 — Scale / SaaS / collaboration / automation

**Outcome:** Public Research OS with teams and automation — **only after P0–P1 signal**.

| # | Work item | Why | Effort |
|---|-----------|-----|--------|
| P4.1 | Billing / entitlements (SaaS-PK B0 manual → later PSP) | Monetize open signup | XL |
| P4.2 | Teams / shared projects + AuthZ ADR | Lab workflows | XL |
| P4.3 | In-app notifications center | Job/sync awareness | L |
| P4.4 | External webhooks + Slack | Automation | L |
| P4.5 | Topic watchers / scheduled research | Product automation | L |
| P4.6 | Writing bi-sync (Docs/Notion) | Export-plus | L |
| P4.7 | DOCX / journal publication packs | Publication | L–XL |
| P4.8 | Evidence Discovery Milestone 2 UX | Writing-first discovery | L |
| P4.9 | Evidence-required Research Assistant | Replace ungrounded chat spine | L |
| P4.10 | Track 2: KG v2 / Novelty | Only with demand + ADR | XL |
| P4.11 | Research Session Engine (ADR-0013) | Durable hub | XL |
| P4.12 | Public Developer API / MCP product | Ecosystem | XL |
| P4.13 | Notebook / PDF annotations | Mark-up product | XL |

---

## 8. First execution slice

**Do not pick randomly.** Follow the strict order in [11-VERSION1-COMPLETION-TRACKER.md](11-VERSION1-COMPLETION-TRACKER.md) §2.

Freeze: no P2+ major capabilities until P0/P1 V1-critical rows are Production Ready.

---

## 9. Dependency diagram

```text
                    ┌─────────────────────┐
                    │  Evidence Platform  │ (frozen — quality only)
                    └──────────┬──────────┘
                               │
         ┌─────────────────────▼─────────────────────┐
         │  P0 Grounded Writing Trust Vertical       │
         │  binder · Reviewer FE · cite insert · α   │
         └─────────────────────┬─────────────────────┘
                               │
         ┌─────────────────────▼─────────────────────┐
         │  P1 Library Durability                    │
         │  worker sync · PDF pull · Settings catalog│
         └─────────────────────┬─────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         P2 Sources      P3 Hardening      (parallel SaaS-PK
         PubMed/Drive    flags/quotas/admin   design only until
                                              open signup)
                               │
                               ▼
                    P4 Teams · Billing · Automation
                               │
                               ▼
              P5 Knowledge Graph (flagship product)
              P6 Research Memory
              P7 Research Agents
              (+ Enterprise E1–E4 · Ecosystem Masterplan)
```

---

## 9b. After P4 — strategic pillars (not feature checklists)

| Phase | Focus | Doc |
|-------|-------|-----|
| **P5** | Knowledge Graph as first-class product | [06](06-KNOWLEDGE-GRAPH-PRODUCT.md) |
| **P6** | Research Memory (nothing forgotten) | [07](07-RESEARCH-MEMORY.md) |
| **P7** | Research Agent Layer | [08](08-RESEARCH-AGENT-LAYER.md) |
| **E1–E4** | Enterprise (audit → RBAC → SAML → SOC2) | [09](09-ENTERPRISE-ROADMAP.md) |
| **Ecosystem** | Every integration changes the product | [10](10-RESEARCH-ECOSYSTEM-MASTERPLAN.md) |

P2 connector work must follow the Ecosystem Masterplan template (why / workflow / KG / Evidence / Writing / Automation) — not “add PubMed” alone.

---

## 10. Success metrics (definition of done for “complete Research OS”)

| Metric | Target |
|--------|--------|
| Lit-review vertical | Unassisted researcher success (Alpha gate) |
| Pipeline | Import→Evidence→WI→Cite→Export with no broken link |
| Trust | Export gated on Reviewer errors |
| Library | Sync via worker; PDFs from ≥1 ref-mgr |
| Honesty | Landing Live/Soon matches code |
| Cost | Chat + WI quota enforced |
| Collab / billing | Explicitly versioned — not fake-complete on landing |

---

## 11. Mapping to prior docs

| This phase | Prior doc |
|------------|-----------|
| P0 | EXECUTION-DUAL-TRACK Phase A validation; EPIC-0004/0005; PLATFORM_FREEZE polish |
| P1–P2 | Integrations verdict / Library Bridge Phase 1b |
| P3 | PRODUCTION_READINESS; SECURITY_BASELINE ops |
| P4 | `docs/public-saas-readiness-pk.md`; IDD-0010; ADR-0013 |
| P5–P7 | [05 Vision](05-RESEARCH-OS-VISION.md), [06](06-KNOWLEDGE-GRAPH-PRODUCT.md)–[08](08-RESEARCH-AGENT-LAYER.md) |
| Enterprise | [09](09-ENTERPRISE-ROADMAP.md) |
| Ecosystem | [10](10-RESEARCH-ECOSYSTEM-MASTERPLAN.md) |

---

## 12. Verdict

Dhund’s path to the original Research OS vision is **finish the OS core, then build the enduring ecosystem**:

1. Close the grounded writing trust gap.  
2. Make library/sync durable.  
3. Add discovery/storage sources through the Ecosystem Masterplan (each connector changes the product).  
4. Harden ops and quotas.  
5. Ship SaaS / teams carefully.  
6. Then flagship **Knowledge Graph**, **Research Memory**, and **Agents** — guided by the North Star lifecycle.

New integrations are valuable — they are not Step 0. Step 0 was this audit.  
**Step 1 is execution against [11-VERSION1-COMPLETION-TRACKER.md](11-VERSION1-COMPLETION-TRACKER.md).**  
Strategic blueprint: [05](05-RESEARCH-OS-VISION.md) onward. Stop writing roadmaps; update the tracker.
