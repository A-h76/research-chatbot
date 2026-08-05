# Dhund — Future

> Roadmap, frozen work, and known debt — for strategy slides. Audited 2026-08.  
> Do **not** treat frozen pillars as “next sprint” without the competitive gate.

---

## North star

Durable Research OS loop (vision):

```text
Question → Discovery → Evidence → Memory → Knowledge
        → Writing → Review → Publishing → Monitoring
```

Today’s spine is strong through **Evidence → Writing → Review → Cite**.  
**Knowledge Graph, Agents, Monitoring, Enterprise** are intentional later chapters.

Vision docs: `docs/audit/05-RESEARCH-OS-VISION.md`, `docs/VISION_PROGRESS.md`.

---

## Near-term (product-critical polish)

From completion audits — ship before expanding pillars:

| Item | Why it matters |
|------|----------------|
| Reviewer FE + export gate | Close the write → defend loop |
| Citation insert-into-draft UX | Writing feels complete |
| WI binder quality | Grounded writing trust |
| Worker `library_sync` completeness | Connect reliability |
| PDF / full-text pull completeness | Evidence needs text |
| Chat / WI quota enforcement | Beta cost control |
| Marketing `/trust` page | Trust Layer visible outside landing section |
| Brand sweep leftovers | Soro / “Personal AI” strings |

Refs: `docs/audit/02-PRODUCT-COMPLETION-AUDIT.md`, `docs/audit/04-RESEARCH-OS-ROADMAP.md` (P0–P1).

---

## Mid-term roadmap (P2–P4)

| Track | Direction |
|-------|-----------|
| Discovery / storage | More providers; harden UFTR; richer library sync |
| Hardening | Observability, quotas, entitlement ledger usage |
| SaaS readiness | Plans (Researcher / Lab / Institution), billing hooks |
| Collaboration | Shared projects, roles (pre-enterprise) |

Dual-track exec notes: `docs/roadmap/EXECUTION-DUAL-TRACK.md`.

---

## Frozen pillars (gate before Phase 3)

**Gate doc:** `docs/audit/16-COMPETITIVE-REPLACEMENT-REVIEW.md`  
Do not auto-build these as the default next epic:

| Pillar | Intent | Doc |
|--------|--------|-----|
| Knowledge Graph (product) | Project knowledge as first-class UI | audit `06` / related |
| Research Memory (productized) | Durable research memory UX | audit `07` |
| Research Agents | Multi-step agent workflows | audit `08` / `10` |
| Literature monitoring | Alerts / continuous discovery | vision P5–P7 |
| Research Session Engine | Deferred — contracts only (ADR-0013) | `docs/adr/0013-…` |

Backend packages may exist (`knowledge_graph/`, etc.) — **product freeze ≠ code absence**.

---

## Enterprise roadmap (E1–E4)

| Phase | Themes |
|-------|--------|
| E1 | Orgs, seats, admin boundaries |
| E2 | SAML SSO, SCIM, RBAC |
| E3 | SOC 2 / ISO programs, audit export, residency |
| E4 | Procurement packaging, SLAs, Trust Center |

Source: `docs/audit/09-ENTERPRISE-ROADMAP.md`.  
Landing already labels SOC2 / SSO / SCIM as **Roadmap** under Trust Layer.

---

## Pricing future (honest)

| Plan | Intent |
|------|--------|
| Researcher | Free / start — personal library + core evidence writing |
| Lab | Shared projects, higher limits, team review |
| Institution | SSO, admin, audit, residency |

Final dollar amounts **not locked** in product — landing uses “Coming soon” placeholders (Stripe-simple).

---

## Ecosystem Coming soon (catalog)

Examples from `backend/ecosystem/catalog.py`:

- Reference: EndNote, Paperpile, ReadCube, JabRef  
- Scholarly: SSRN, IEEE, ACM  
- Storage: Box  
- Writing bridges: Docs, Word, Overleaf, Notion, Obsidian  
- Models: Grok, DeepSeek, Mistral (catalog)  
- Automation: Open API, MCP, Zapier, n8n, webhooks  

---

## Technical debt to plan around (not hide)

| Debt | Stance |
|------|--------|
| Dual storage / upload paths | Accepted V1 (ADR-0014) — don’t “fix” casually |
| Dual AI invoke (SSE chat vs Prompt Engine) | Converge via Capability Router over time |
| Dual cost ledgers | Consolidate carefully |
| Queue / LLM not fully DI-swappable | Named deferred debt (constitution) |
| Dead-ish: `SearchIndex`, `ImportSession` | Cleanup candidates |
| `server.py` monolith size | Extend via blueprints; no rewrite without ADR |

Refs: `docs/00-constitution.md`, `docs/audit/03-TECHNICAL-DEBT-REPORT.md`, ADRs 0001 / 0014 / 0016.

---

## ADRs worth citing on “why future looks like this”

| ADR | Point |
|-----|-------|
| 0001 | Keep Postgres worker — no silent Celery rewrite |
| 0003 | Evidence = canonical research truth |
| 0005 / 0007 | Freeze Evidence / query contracts |
| 0004 / 0006 | Staged RI pipeline |
| 0013 | Session engine deferred |
| 0015 | Universal full-text resolution |
| 0016 | Capability Router backbone |
| 0017 | Research Scope policy |

---

## Design / brand future

- Design Language **v1 frozen** — execute, don’t add new inspiration brands  
- Landing section ownership locked (§8b in design language)  
- App density / border / confidence doctrines continue on remaining surfaces  
- Trust Layer stays SpaceX-austere on marketing only — never black OS shell  

## Engineering evolution (not a rewrite)

Frozen doctrine: [`docs/ENGINEERING-CONSTITUTION-v1.md`](../docs/ENGINEERING-CONSTITUTION-v1.md)

Living (not more constitutions):

| Doc | Role |
|-----|------|
| [`ENGINEERING-EVOLUTION-TRACKER.md`](../docs/ENGINEERING-EVOLUTION-TRACKER.md) | Current → Target → Priority (AI dual→Router, ledger unify, …) |
| [`ARCHITECTURE-HEALTH.md`](../docs/ARCHITECTURE-HEALTH.md) | 7 scored KPIs — baseline **3.0 / 5** |

- **Don’t clean for aesthetics** — Platform Layers vs Product Domains  
- Keep DB / migrations / APIs / queue / worker; peel `server.py` deliberately  
- **80% capability / 20% debt** — never Cleanup-only sprints  
- **Stop adding constitution-class docs** — implement Tracker High rows next  



---

## Suggested future narrative for slides

1. **Where we are** — personal Research OS, Evidence First, closed beta  
2. **Close the loop** — Reviewer + cite + Connect reliability  
3. **Open the lab** — shared projects + Lab plan  
4. **Earn the institution** — Trust Layer roadmap (SSO, SOC2, audit)  
5. **Only then** — Graph / Agents / Monitoring after competitive gate  

---

## Slide prompts

1. North-star loop (highlight shipped vs future nodes)  
2. Next 90 days polish list  
3. Frozen pillars (with “gate” callout)  
4. Enterprise ladder E1–E4  
5. Debt we accept vs debt we schedule  
6. Competitive replacement gate  

---

## Source paths

- `docs/audit/04-RESEARCH-OS-ROADMAP.md`  
- `docs/audit/05-RESEARCH-OS-VISION.md`  
- `docs/audit/09-ENTERPRISE-ROADMAP.md`  
- `docs/audit/16-COMPETITIVE-REPLACEMENT-REVIEW.md`  
- `docs/VISION_PROGRESS.md`  
- `docs/roadmap/EXECUTION-DUAL-TRACK.md`  
- `docs/adr/*`  
- `backend/ecosystem/catalog.py`  
