# Universal Full-Text Resolution (UFTR) — platform contract

**Service:** Universal Full-Text Resolution  
**Version:** 1.0  
**Status:** Production Ready  
**ADR:** [ADR-0015](../adr/0015-universal-full-text-resolution-v1.md)  
**Package:** `backend.scholarly.uftr`

## Platform rule

UFTR is a **platform service**. Future integrations that need full text from a
paper *reference* must not know how to fetch PDFs.

They call **`resolve_and_attach(...)`** and stop.

```text
Discover / scholarly import / retry
        │
        ▼
  resolve_and_attach(...)     ← only public acquisition API for URL→content
        │
        ▼
  Research Content (PDF today)
        │
        ▼
  apply_pdf_bytes_to_stub → enqueue import → SUE → Evidence → Writing
```

## Primary API

```python
from backend.scholarly.uftr import resolve_and_attach, UFTR_VERSION

assert UFTR_VERSION == "1.0"

result = resolve_and_attach(
    db,
    user_file,                 # metadata stub (UserFile)
    storage=storage,
    upload_dir=upload_dir,
    enqueue_import=enqueue_import,
    user_id=user_id,
    max_file_mb=50,
    work=None,                 # optional provider work: doi, open_access_url, pmcid, …
    force=False,               # True = bypass negative cache / age gates
)
```

### Return shape (stable for 1.0)

| Field | Type | Meaning |
|-------|------|---------|
| `pdf_attached` | bool | Bytes stored on stub |
| `analysis_queued` | bool | Shared `import` job enqueued |
| `pdf_error` | str \| null | Outcome code or attach error (`FOUND` never here on success) |
| `fulltext` | object \| null | Public provenance summary for UI / toasts |

`fulltext` includes: `outcome`, `user_reason`, `full_text_source`, `attempts`,
`last_attempt_at`, `found`.

### Outcome enum (engineering)

```text
FOUND
NO_OPEN_ACCESS
PUBLISHER_PAYWALL
BOT_PROTECTION
INVALID_RESPONSE
NETWORK_ERROR
TIMEOUT
```

UI collapses bot/paywall into soft copy (“Publisher restrictions”); Details
shows the enum + resolver attempts.

## Supporting APIs (not for “how do I download a PDF?”)

| Symbol | Use |
|--------|-----|
| `resolve_full_text` | Resolve/validate only (tests, diagnostics) |
| `should_auto_retry` / `fulltext_payload` / `lifecycle_label` | State + UI |
| `record_manual_attach` | After user Attach PDF (bytes path) |
| `POST /api/library/files/<id>/fetch-fulltext` | HTTP wrapper around `resolve_and_attach` |

## Bytes already in hand

When the caller **already has PDF bytes** (upload, Drive, Dropbox, OneDrive,
Zotero/Mendeley pull, manual attach), do **not** call UFTR. Use
`apply_pdf_bytes_to_stub` → enqueue import (Golden Rule attach).

UFTR is for **reference → Research Content**, not byte re-upload.

## Forbidden for new code

- Calling `pubmed.download_open_access_pdf` / `arxiv.download_pdf` / etc. from
  library or Discover routes
- Per-connector HTTP “try this URL and hope it’s a PDF”
- Cloudflare / paywall bypass automation

Provider download helpers may remain for internal scholarly tests or as
resolver inputs; they are **not** the platform integration surface.

## HTTP surface

| Method | Path | Role |
|--------|------|------|
| POST | `/api/library/files/<id>/fetch-fulltext` | Manual / event-driven retry (`force`, `auto`) |
| POST | `/api/library/files/<id>/attach` | Manual bytes (records `full_text_source: manual`) |
| POST | `/api/discover/import` | Creates stub then `resolve_and_attach` |

## Versioning

- Additive fields on `fulltext` / return dict: allowed without major bump.
- Removing outcomes, renaming `resolve_and_attach`, or reopening per-provider
  fetch in acquisition routes: **breaking** → ADR + `UFTR_VERSION` bump.
