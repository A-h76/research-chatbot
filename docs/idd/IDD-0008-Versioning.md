# IDD-0008 — Versioning & Deprecation

| Field | Value |
|-------|-------|
| **Status** | Proposed |

---

## 1. What is versioned

| Artifact | Field / mechanism | Breaking change means |
|----------|-------------------|------------------------|
| HTTP API | Path `/api` as **v1**; future `/api/v2` | Remove/rename field; change meaning |
| EvidenceObject | `pipeline_version` | Extract semantics change |
| EvidenceQuery | ADR + IDD constants | Remove intent; add forbidden-key violation |
| Grounded writing | `writing_version` | Response shape change |
| Reviewer | `reviewer_version` | Issue code semantics change |
| IDD pack | Document header Status + date | This pack revision |
| Events | `schema_version` | Payload rename |

---

## 2. API versioning policy

### Current

- Unversioned `/api/*` = **API v1**.
- Additive JSON fields are **non-breaking**.
- Frontend MUST ignore unknown fields.

### Future breaking changes

1. Write ADR + update IDD-0003.
2. Ship `/api/v2/...` **or** version header `Accept: application/vnd.dhund.v2+json` (choose one in ADR—prefer path for clarity).
3. Dual-run ≥ one release: v1 and v2 both work.
4. Deprecate v1 with documented sunset date (≥ 90 days for external clients; internal SPA can migrate faster).

---

## 3. Deprecation policy

| Step | Action |
|------|--------|
| 1 | Mark field/endpoint `deprecated` in IDD + OpenAPI description |
| 2 | Emit warning header optional: `Deprecation: true` / `Sunset: <date>` |
| 3 | Frontend migrates; Backend keeps behavior |
| 4 | Remove only after sunset + usage metrics near zero |

**Never** silently change EvidenceObject status meanings.

---

## 4. Database migration strategy

1. Expand/contract: add columns nullable → backfill → tighten.
2. Avoid renames in place; add new + dual-read → drop old.
3. Partial indexes for lifecycle (evidence status) preferred over hard deletes.
4. `create_all` does not alter columns—always ship `migrations/NNNN_*.sql`.

---

## 5. Compatibility matrix (v1)

| Client | Server | Supported |
|--------|--------|-----------|
| SPA expecting `file_id` | API returns `file_id` + optional `paper_id` | Yes |
| SPA sending EvidenceQuery with `model` | Server | **Must 400** |
| Old worker job_type in flight | New worker | Handler remains until drained |

---

## 6. Document control

IDD changes require:

1. PR titled `idd: …`
2. Sign-off from Developer A and B on breaking sections
3. Link to ADR if platform freeze impacted
