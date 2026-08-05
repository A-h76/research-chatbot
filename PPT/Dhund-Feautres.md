# Dhund — Features

> Feature inventory for slides. Spelling filename as requested: `Dhund-Feautres.md`.  
> Status labels: **Shipped** · **Beta polish** · **Coming soon** · **Frozen / later**.

---

## Spine features (Research OS)

| Feature | Status | What it does |
|---------|--------|--------------|
| Projects | Shipped | Research hubs with papers, questions, notes, writing |
| Library / upload | Shipped | PDF upload, batches, pipeline status, duplicates/health |
| Library Connect | Shipped (partial) | Zotero, Mendeley, BibTeX/RIS, Drive/Dropbox/OneDrive — catalog-driven Live vs Soon |
| Discover / Search | Shipped | OpenAlex + scholarly providers; in-library search |
| Paper workspace | Shipped | Overview, structure, entities, evidence, narrative, related, chat |
| Paper analysis / SUE | Shipped (Phase 2A) | Structured understanding pipeline on papers |
| Evidence layer | Shipped / frozen contract | Extract, accept, inspect claims with provenance |
| Research Intelligence (RI) | Shipped / frozen | Search, rank, consensus, conflict, reason, grounded writing |
| Writing Studio | Shipped | Drafts, versions, autosave, evidence bindings |
| Research Reviewer | Shipped backend · FE polish | Findings vs evidence; persistence tables live |
| Citations / BibTeX | Shipped | Bibliography + export paths |
| Notes | Shipped | Project / freeform notes |
| Memory | Shipped (early) | Research memory kinds; productization continues |
| Streaming chat | Shipped | Tool inside OS; project/paper scoped |
| Multi-paper compare / gaps | Shipped | `/research/compare` + derived analyses |
| Pipeline visibility | Shipped | Job stages, AI state chips, progress honesty |
| In-app Docs | Shipped | `/docs` — contracts + ADRs |
| Onboarding | Shipped | Role / fields wizard |
| Settings | Shipped | Account, research defaults, integrations, data controls |
| Admin ops | Shipped | Invites, flags, quotas, kill switch, security events, worker health |
| Closed-beta auth | Shipped | Google, magic link, password, invites |
| Security baseline | Shipped (docs + controls) | TLS, export/delete, project-scoped evidence, API auth |
| Landing (section-owned) | Shipped | Tesla→…→Trust→Pricing marketing page |

---

## Evidence & RI (detail)

**Evidence objects** are the research truth:

- Claim / quote / locators (page, section)  
- Confidence / support bands  
- Accept → usable in writing  
- Bindings: manuscript span ↔ evidence  

**RI stages (contract freeze):**

| Stage | Intent |
|-------|--------|
| Search / Rank | Find & order evidence |
| Consensus / Conflict | Agreement vs tension across sources |
| Reason | Explain with provenance |
| Writing (WI) | Grounded draft generation gated on accepted evidence |
| Reviewer | Critique writing against evidence |

Contracts: `docs/contracts/` · RI freeze docs under `docs/contracts/` / audit pack.

---

## Library & acquisition

| Capability | Status |
|------------|--------|
| Direct PDF upload | Live |
| Bulk upload | Live |
| BibTeX / RIS import | Live |
| Zotero / Mendeley | Live (catalog) |
| Google Drive / Dropbox / OneDrive | Live (catalog) |
| OpenAlex discover | Live |
| PubMed / arXiv / Europe PMC / Crossref / S2 | Live clients / catalog |
| EndNote / Paperpile / ReadCube / JabRef | Coming soon |
| SSRN / IEEE / ACM | Coming soon |
| Overleaf / Notion / Obsidian export bridges | Coming soon |
| Full-text resolution (UFTR) | Platform service (ADR-0015) |

Honesty rule: UI must show **Coming soon** for non-live catalog entries (`backend/ecosystem/catalog.py`).

---

## AI / Prompt Engine

| Capability | Status |
|------------|--------|
| Capability Router (Job → Profile → Policy → Model) | Shipped (ADR-0016) |
| Research Scope gateway (ALLOW / CLARIFY / REDIRECT) | Shipped (ADR-0017) |
| Cost ledger / usage | Shipped |
| Personas / prompt versions | Shipped (admin/AI surfaces) |
| Multi-provider catalog (Anthropic, Gemini, …) | Catalog live; routing expands |
| Agents as product pillar | Frozen / later |

---

## Trust Layer (Available vs Roadmap)

### Available now
- Encryption in transit (TLS)  
- Encryption at rest (when object storage configured)  
- Project-scoped evidence (writing gated)  
- Account export & delete  
- Authenticated APIs  
- GDPR-ready controls (expanding formal program)  
- Reproducibility hashes on WI drafts (RI-009)  

### Roadmap
- SOC 2 Type II  
- ISO 27001  
- Explicit zero training commitment in policy  
- SAML SSO  
- SCIM + RBAC  
- Exportable audit logs · data residency  
- Marketing `/trust` Trust Center page  

---

## Collaboration & enterprise (not V1 spine)

| Feature | Status |
|---------|--------|
| Shared lab projects | Coming soon / Lab plan |
| Comments / realtime collab | Later |
| Orgs / billing / seats | Enterprise roadmap (E1–E4) |
| Knowledge Graph product UI | Frozen pending competitive review |
| Research Agents product | Frozen / later |
| Continuous monitoring of literature | Vision P5–P7 |

---

## Feature → database (quick map)

| Feature | Tables |
|---------|--------|
| Library | `files`, `chunks`, `upload_jobs`, `storage_usage` |
| Connect | `library_connections`, collections, `library_sync_runs` |
| Evidence | `evidence_objects`, `claim_reviews`, `evidence_extraction_runs` |
| Writing | `documents`, `document_versions`, `writing_sentence_bindings` |
| Reviewer | `reviewer_runs`, `reviewer_findings` |
| Chat | `conversations`, `messages` |
| Citations / notes / memory | `citations`, `notes`, `memories` |
| Admin / quotas | `feature_flags`, `usage_logs`, `ai_usage_ledger`, `users` quota cols |

---

## Slide prompts

1. Spine checklist (7 stages)  
2. Evidence First deep-dive  
3. Library Connect Live vs Soon  
4. Writing + Reviewer  
5. Trust Layer two columns  
6. What we refuse to fake (agents/KG until ready)  

---

## Source paths

- `docs/VISION_PROGRESS.md`  
- `docs/audit/12-PHASE2-COMPLETION-TRACKER.md`  
- `docs/audit/02-PRODUCT-COMPLETION-AUDIT.md`  
- `backend/ecosystem/catalog.py`  
- `docs/contracts/`  
- Landing Trust copy in `templates/login.html`  
