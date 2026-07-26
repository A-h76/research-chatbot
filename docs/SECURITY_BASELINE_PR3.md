# Security Baseline Report — PR3

**Date:** 2026-07-26  
**Scope:** Upload magic-byte MIME validation + optional ClamAV  
**Status:** Complete (PR3 only — PR4 not started)

---

## Changes delivered

### 1. Magic-byte validation (required)
- New: `backend/upload/magic_bytes.py`, `backend/upload/errors.py`
- Sniffs PDF, PNG, JPEG, GIF, WEBP, text, and ZIP-based Office/EPUB
- ZIP subtypes verified by archive layout (docx/`word/`, pptx/`ppt/`, xlsx/`xl/`, epub `mimetype`)
- Canonical MIME stored (client `Content-Type` no longer trusted)
- Error code: `invalid_mime`

### 2. Unified upload policy
| Path | Extensions | Magic + ClamAV |
|------|------------|----------------|
| `POST /api/files` | documents + images | yes (on temp file) |
| `POST /api/uploads/presign` | extension allowlist | confirm-time sniff |
| `POST /api/uploads/confirm` | full sniff + scan | yes (local_copy) |
| `POST /api/documents/upload` | documents | yes (in-memory) |
| `POST /api/uploads/bulk` | documents | yes (in-memory) |

Documents: `.pdf .epub .docx .txt .pptx .xlsx`  
Images (session library): `.png .jpg .jpeg .gif .webp`

### 3. Optional ClamAV
- `backend/upload/clamav.py`
- **Disabled by default** (fail-open)
- When `CLAMAV_ENABLED=1`: fail-closed if clamd unreachable; `virus_detected` → quarantine under `CLAMAV_QUARANTINE_DIR`
- TCP (`CLAMAV_HOST`/`CLAMAV_PORT`) or Unix (`CLAMAV_SOCKET`)

### 4. Explicit non-changes
- No Phase 1/2 / PromptBuilder changes
- No CSP / session TTL (PR4)
- No mandatory ClamAV daemon in CI

---

## Test evidence
```
64 passed — backend/upload/test_magic_bytes.py, test_clamav.py,
test_upload.py, test_bulk.py, tests/test_bulk_upload.py
```

---

## Files touched
- `backend/upload/errors.py`, `magic_bytes.py`, `clamav.py`, `validation.py`
- `backend/upload/routes.py`, `bulk.py` + tests
- `server.py` (`/api/files`, presign, confirm)
- `tests/test_bulk_upload.py`, `.env.example`
- `docs/SECURITY_BASELINE_PR3.md`

---

## Residual risk (deferred)
- CSP / security headers / session idle+absolute TTL → PR4  
- Presign still accepts bytes to object storage before confirm sniff (rejected + deleted on confirm)  
- Deep OLE/.doc legacy formats remain unsupported (rejected)  

---

## Ops checklist
1. No new required deps for magic sniffing  
2. To enable AV: run clamd, set `CLAMAV_ENABLED=1` + host/socket  
3. Monitor `invalid_mime` / `virus_detected` / `clamav_unavailable` logs  
