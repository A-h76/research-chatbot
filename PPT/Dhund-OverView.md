# Dhund — Overview

> Read this to draft slides manually. Facts audited from the codebase (2026-08).

---

## One-liner

**Dhund is a Research Operating System** — a private workspace to discover, understand, write, review, and publish research with evidence you can inspect and defend.

Not a ChatGPT skin. Chat is a tool inside the OS, not the product.

**Brand line (design language):**  
*A light-first research instrument. Nothing feels magical — everything feels inspectable.*

---

## Who it’s for

| Audience | Today | Later |
|----------|-------|-------|
| Individual researchers (MSc / PhD / postdoc) | Closed beta (invite-gated) | Open researcher plan |
| Labs / supervisors | Waitlist / early access | Shared projects |
| Institutions | Roadmap | SSO, audit, residency |

---

## The research loop (spine)

```text
Question → Discovery → Library → Evidence → Writing → Review → Publish
```

Supporting systems around the spine:

- **Memory** — durable claims and preferences  
- **Knowledge** — project-scoped understanding  
- **Pipeline / AI Router** — every AI job is policy-gated and ledgered  
- **Trust Layer** — security, privacy, reproducibility, audit  

---

## What ships today (honest summary)

| Strength | Gap |
|----------|-----|
| Evidence platform + RI stages | Graph / Agents productized later |
| Library upload + Connect (Zotero, Drive, …) | Some connectors = Coming soon |
| Writing Studio + grounded drafts | Reviewer FE polish still open |
| Streaming chat + paper workspace | Not the OS spine |
| Closed-beta auth + admin ops | Orgs / billing / SAML = roadmap |
| Living API contracts (Evidence / RI / jobs) | `/trust` marketing page still missing |

---

## Product identity

| Concept | Meaning |
|---------|---------|
| **Evidence First** | Accepted evidence objects are the only research truth for writing |
| **Inspectable** | Claims → spans → PDF passages → confidence |
| **Capability Router** | Research Job → Capability → Policy → Provider → Evidence → Ledger |
| **Research Scope** | ALLOW · CLARIFY · REDIRECT — prompts stay in research scope |
| **Trust Layer** | Institutional credibility (security → compliance → privacy → audit) |

---

## Architecture at a glance

```text
React SPA (Vite)  ←→  Flask monolith (server.py)
                            │
                            ├── Postgres (source of truth)
                            ├── Worker (queue jobs)
                            ├── Redis (optional job status cache)
                            └── Object storage (local / R2 / S3)
```

- **Frontend:** `frontend/` — feature folders (library, evidence, writing, …)  
- **Backend:** `server.py` + `backend/` blueprints + `worker.py`  
- **Docs freeze:** `docs/contracts/`  
- **Design governance:** `docs/DHUND-DESIGN-LANGUAGE-v1.md`  

---

## Database — domain map (audit)

Core truth lives in Postgres. SQLite is local/dev only (worker needs Postgres).

| Domain | Main tables |
|--------|-------------|
| Auth / users | `users`, invite/magic/password tokens, `security_events` |
| Projects | `projects` |
| Chat | `conversations`, `messages` |
| Library / files | `files`, `chunks`, `upload_*`, `storage_usage` |
| Queue | `upload_jobs`, `outbox_events`, `worker_heartbeats` |
| Evidence | `evidence_objects`, `claim_reviews`, `evidence_extraction_runs` |
| Writing | `documents`, `document_versions`, `writing_sentence_bindings` |
| Reviewer | `reviewer_runs`, `reviewer_findings` |
| Decisions | `research_decisions`, `workflow_events` |
| Library Connect | `library_connections`, collections, `library_sync_runs` |
| Quotas / AI cost | `usage_logs`, `ai_usage_ledger`, feature flags |
| Prompt Engine | `prompt_versions`, `personas`, `prompt_executions`, `model_*` |

**Migrations:** `0001`–`0040` under `migrations/` (upload → evidence → writing → UFTR).

**Boot order (fresh DB):** app `create_all` (core tables) → `run_migrations.py` → `backfill.py`.

---

## Data flow (upload → publish)

```text
Upload / Connect
  → files + upload_jobs + outbox
  → worker: import → chunks → metadata / paper analysis
  → evidence_extract → evidence_objects
  → Writing Studio binds sentences → evidence
  → claim_reviews / research_decisions
  → reviewer_runs
  → cite / export (BibTeX, Markdown)
```

---

## Competitive position (how to say it)

| Others | Dhund |
|--------|-------|
| Summarize a PDF in chat | End-to-end Research OS |
| Citation generators | Evidence-bound writing |
| Reference managers alone | Library + evidence + write + review |
| “AI wrote it” | Inspectable provenance + confidence |

---

## Slide prompts (write these yourself)

1. Title + one-liner  
2. Who / closed beta  
3. Research loop diagram  
4. Evidence First (one visual)  
5. Stack diagram  
6. Honest “shipped vs roadmap”  
7. Trust Layer (Available vs Roadmap)  

---

## Source paths

- `docs/DHUND-DESIGN-LANGUAGE-v1.md`  
- `docs/audit/05-RESEARCH-OS-VISION.md`  
- `docs/audit/02-PRODUCT-COMPLETION-AUDIT.md`  
- `docs/contracts/README.md`  
- `CLAUDE.md` · `docs/00-constitution.md`  
- `server.py` models · `migrations/`  
