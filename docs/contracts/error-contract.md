# A-402 — Error Contract

**Status:** Frozen (A-402)  
**contracts_version:** `1.2.0`  
**Code:** `backend/evidence/api/errors.py` + route `_err` helpers  
**Parent:** [IDD-0003 §1.6](../idd/IDD-0003-API-Contracts.md)

---

## 1. Standard error body (v1)

```json
{
  "error": "validation_error",
  "detail": "Human-readable explanation"
}
```

| Field | Required | Notes |
|-------|----------|--------|
| `error` | yes | Machine code (string) |
| `detail` | yes* | Human message (`*` always set by Evidence `_err`; treat as required for clients) |
| `fields` | no | Reserved for field-level maps; **not currently emitted** by Evidence routes |

Frontend `apiClient` reads `body.detail || body.error` on non-OK responses.

**Not used on v1 Evidence routes:** `{ "errors": [] }` arrays or `{ data, meta, errors }` envelopes.

---

## 2. Canonical ErrorCode values

| Code | Typical HTTP | Meaning |
|------|--------------|---------|
| `validation_error` | **422** | Bad JSON / EvidenceQuery / binding payload |
| `not_found` | **404** | Missing resource **or** cross-user ownership hide |
| `authz_denied` | **403** | Mapped in helpers; ownership often surfaces as `not_found` instead |
| `rate_limited` | **429** | When emitted as domain error |
| `not_research_ready` | **400** | Extract preflight |
| `internal_error` | **500** | Reserved |

Clients should branch on **`error` string + HTTP status**, not status alone.

---

## 3. Extract-specific error codes (frozen)

These appear in `error` and may include extra diagnostic fields on the **same** JSON object:

| `error` | HTTP | Extra keys commonly present |
|---------|------|-----------------------------|
| `not_research_ready` | 400 | `status`, `reason`, `objects_created`, `run_id`, `job_id`, `pipeline_version` |
| `missing_phase1` | 409 | same pattern |
| `already_running` | 409 | `status`, `job_id`, `pipeline_version`, … |

Treat extra keys as **additive diagnostics**; `error` + HTTP remain the contract.

---

## 4. Success-vs-error distinctions (important)

| Situation | HTTP | Body |
|-----------|------|------|
| Writing blocked (insufficient evidence) | **200** | RI envelope; `writing.status = "blocked"`; `writing.blocked_reason` |
| Invalid EvidenceQuery | **422** | `{ error: "validation_error", detail }` |
| Forbidden model knobs on query | **422** | same |
| Unknown evidence id | **404** | `{ error, detail }` |

Do **not** treat `blocked_reason` strings as HTTP `error` codes.

---

## 5. Auth & rate limit

| Case | Behavior |
|------|----------|
| No session | `401` or `302` to login |
| Limiter trip | `429` — body may be Flask-Limiter default; prefer checking status code |

Stabilizing Limiter bodies to `{ error: "rate_limited", detail }` is a **compatible** follow-up (additive alignment), not required to call A-402 done.

---

## 6. Client rules

1. Prefer `detail` for toast/copy; fall back to `error`.  
2. Ignore unknown keys on error objects.  
3. Do not assume `fields` is present.  
4. Map `422` → form/validation UX; `404` → missing or inaccessible; `409` → conflict/retry extract.
