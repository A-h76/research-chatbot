# WF-001 — Import Contract

**Status:** Frozen (Workflow Contracts v1.0)  
**contracts_version:** `1.3.0`  
**Workflow step:** `Import` (+ feeds `UFTR` when reference-only)  
**Source of truth:** `backend/library/import_service.py` · `backend/upload/upload_service.py`  
**Freeze pack:** [../WF-v1.0-COMPLETE-FREEZE.md](../WF-v1.0-COMPLETE-FREEZE.md)

---

## 1. Input

| Kind | Required | Notes |
|------|----------|--------|
| `user_id` | yes | Owner of the library row |
| `project_id` | optional | Project-scoped corpus when known |
| Identity | yes | Title / DOI / external `(provider, item_id)` / or held bytes |
| Acquisition edge | yes | Discover, upload, Drive, OneDrive, manual attach, … |

**Entry points (many):** PubMed, arXiv, ORCID, OpenAlex, Europe PMC, session `/api/files`, JWT documents, bulk, presign confirm, Drive/Dropbox/OneDrive, manual Attach PDF.

**Not input:** Provider-specific “how to fetch PDF” after a reference exists — that is [UFTR](../uftr-contract.md).

---

## 2. Output

| Artifact | Meaning |
|----------|---------|
| `UserFile` stub or updated row | Canonical library paper identity |
| `created` / `already_exists` | Dedupe outcome |
| Optional attach + `import` job | Bytes on storage + Postgres queue enqueue |
| WorkflowInstance | `Import` → `completed`; `UFTR` or `SUE` started/skipped |

Stable spine result fields (ImportService): `spine`, `file`, `created`, `already_exists`, attach/queue flags when applicable.

---

## 3. Invariants

1. **One Import implementation** — `ImportService` owns library import policy after acquisition; UploadService owns accept/store then delegates enqueue to ImportService (or shared outbox helper).
2. **Many entry points, one spine** — providers may differ only in auth / metadata / bytes acquisition.
3. **No per-provider full-text forks** — reference → PDF goes through UFTR (`resolve_and_attach`); held bytes use attach, not UFTR.
4. **Dedupe before create** — DOI or external identity must not create a second live row for the same user.
5. **Never `import server`** from library/upload packages — factory/DI only.
6. Dual storage façades (session vs JWT) remain allowed (ADR-0014); they must not fork import *policy*.

---

## 4. Events

| Domain event | When |
|--------------|------|
| `PaperImported` | New library row acquired (not a dedupe hit) |

| Workflow step | Transition |
|---------------|------------|
| `Import` | → `completed` |
| `UFTR` | → `running` (reference) or `skipped` (held PDF) |
| `SUE` | → `running` when analysis queued after held PDF / UFTR success |

Worker `job_type=import` may note Import again (idempotent if already completed).

---

## 5. Ownership

| Owns | Does not own |
|------|----------------|
| **Library** — ImportService, identity, dedupe, enqueue policy | Discover HTTP / OAuth (Discovery edges) |
| **Upload** — UploadService accept/store façades | Evidence extract, SUE LLM, Writing |
| **UFTR** (platform) — reference → full text | Re-uploading bytes the caller already holds |

**PR gate:** A second “import this paper into the library” implementation requires ADR + retirement plan.
