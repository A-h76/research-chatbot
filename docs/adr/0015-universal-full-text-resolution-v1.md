# ADR-0015: Universal Full-Text Resolution (UFTR) v1.0 — platform service

Status: accepted  
Date: 2026-08-04

## Context

Discover and scholarly providers previously each knew “how to fetch a PDF”
(`download_open_access_pdf`, provider-specific HTTP). That duplicated validation,
produced silent metadata-only stubs (stuck at Understanding), and would force
every future connector to re-learn bot/paywall/OA edge cases.

Product Hardening #1 shipped **Universal Full-Text Resolution (UFTR)** as a
shared resolve → validate → attach path. It must be treated as a **platform
service**, not a Discover convenience.

## Decision

**UFTR v1.0 is Production Ready** and frozen as a platform boundary.

### Integration contract (binding)

Future acquisitions that start from a **paper reference / DOI / OA URL** (not
already-held bytes) **must not** implement PDF fetch logic. They call:

```python
from backend.scholarly.uftr import resolve_and_attach

resolve_and_attach(
    db,
    user_file,
    storage=storage,
    upload_dir=upload_dir,
    enqueue_import=enqueue_import,
    user_id=user_id,
    max_file_mb=max_file_mb,
    work=optional_provider_work,  # identity + OA hints only
    force=False,
)
```

UFTR owns:

1. Resolver Chain (candidate discovery)
2. Validator (FOUND vs failure outcomes)
3. Provenance (`fulltext_json`)
4. Soft-fail outcomes for UI / KPIs
5. Attach + enqueue via the Golden Rule (`apply_pdf_bytes_to_stub` → `import`)

### What stays outside UFTR

| Path | Why |
|------|-----|
| Upload / Drive / Dropbox / OneDrive / Zotero pull / manual Attach PDF | Caller **already has bytes** → `apply_pdf_bytes_to_stub` directly |
| Provider `download_*` helpers under `backend/scholarly/{pubmed,arxiv,…}` | **Internal / legacy** — not the acquisition API; may feed resolvers or tests only |

### Non-goals (still binding)

- No Cloudflare challenge bypass
- No paywall / shadow-library circumvention
- No claim that every publisher PDF is obtainable

### Version

- **Service:** Universal Full-Text Resolution  
- **Version:** `1.0` (`backend.scholarly.uftr.UFTR_VERSION`)  
- **Status:** Production Ready  
- **Living contract:** [`docs/contracts/uftr-contract.md`](../contracts/uftr-contract.md)

Breaking changes to `resolve_and_attach` return shape, outcome enum, or
“integrations fetch PDFs themselves” require a new ADR and version bump.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Keep per-provider download in Discover | Re-forks bot/paywall handling; OpenAlex gap returns |
| Expose Resolver + Validator as the public API | Callers reassemble attach/enqueue incorrectly |
| Fold UFTR into each connector package | Not a platform service; Golden Rule drifts |

## Consequences

- New scholarly / Discover-like connectors: **hints in, `resolve_and_attach` out**.
- Paper Overview / Library speak Full Text Needed language; Details show outcomes.
- HTML / XML / JATS Research Content can extend Validator later without renaming UFTR
  or changing the integration call.

## Cost / Security / Observability / Extensibility

- **Cost:** Unpaywall + OpenAlex lookups; capped candidates; resolver cache TTLs.  
- **Security:** Legal OA sources only; no bot bypass.  
- **Observability:** `fulltext_json` + library health `fulltext_resolution`.  
- **Extensibility:** New resolvers plug into the chain; callers stay on `resolve_and_attach`.
