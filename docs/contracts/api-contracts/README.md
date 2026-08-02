# API Contracts (living index)

**Owner:** Developer A  
**Parent:** [IDD-0003](../../idd/IDD-0003-API-Contracts.md)  
**Freeze pack:** [../api-contracts.md](../api-contracts.md) (A-402–A-405)  
**contracts_version:** 1.2.0  

## Purpose

Day-to-day index of route names. **Authoritative request/response shapes for Evidence/RI/jobs live in the freeze pack** — if this index and the freeze disagree, the freeze wins until IDD is updated.

## Frozen route index (v1.2 — Evidence / RI / Reviewer / Jobs)

| Method | Route | Auth | Primary DTO |
|--------|-------|------|-------------|
| GET | `/api/projects/{id}/evidence` | Session | `{ items: EvidenceObject[], count, total, limit, offset }` |
| GET | `/api/evidence/{id}` | Session | `EvidenceObject` |
| POST | `/api/projects/{id}/evidence/extract` | Session | Job / run matrix |
| POST | `/api/evidence/{id}/reviews` | Session | `{ ok, evidence }` |
| POST | `/api/evidence/explain` | Session | Explain DTO |
| POST | `/api/evidence/search` \| `retrieve` | Session | RI envelope |
| POST | `/api/evidence/rank` | Session | RI + ranking |
| POST | `/api/evidence/consensus` | Session | RI + `consensus` |
| POST | `/api/evidence/conflict` | Session | RI + `conflict` |
| POST | `/api/evidence/reason` | Session | RI + `reasoning` |
| POST | `/api/evidence/writing` | Session | RI + nested `writing` |
| POST/GET/DELETE | evidence-bindings | Session | Binding DTO |
| GET | `/api/documents/{id}/reviewer-runs` | Session | ReviewerRun[] |
| GET | `/api/documents/{id}/reviewer-runs/latest` | Session | ReviewerRun + findings |
| GET | `/api/reviewer-runs/{id}` | Session | ReviewerRun + findings |
| GET | `/api/jobs/{id}/status` | Session | Job status (+ A-404 lifecycle/retry/timings) |

## Other surfaces (indexed, not fully re-frozen in A-402)

| Method | Route | Auth | Primary DTO |
|--------|-------|------|-------------|
| GET | `/api/me` | Session/JWT | `User` |
| GET | `/api/auth/jwt` | Session | `{ access, expires_in }` |
| GET/POST/PATCH | `/api/projects`… | Session | `Project` |
| GET/POST/DELETE | `/api/files`… | Session | `Paper` (alias file) |
| POST | `/api/documents/upload` | JWT | `Paper` + job |
| GET | `/api/usage` | Session | Entitlement usage summary (+ soft-warn) |
| GET/PATCH | `/api/admin/ops/quotas/<user_id>` | Admin | Inspect / set limits / plan |
| POST | `/api/admin/ops/quotas/<user_id>/reset` | Admin | Reset monthly usage |
| GET/POST | `/api/admin/ops/quotas/disabled` | Admin | Temporarily disable quotas |
| GET | `/api/admin/ops/quotas/analytics` | Admin | Consumption by operation / user |
| GET | `/api/integrations/catalog/public` | Public | Live / Coming Soon for landing honesty |
| GET | `/api/library/connections` | Session | Connection status (legacy; prefer catalog) |
| GET | `/api/library/health` | Session | Readiness + need_pdf counts |
| GET/POST | `/api/library/duplicates`… | Session | Duplicate groups + merge |
| POST | `/api/library/files/<id>/attach` | Session | Attach PDF to stub |
| POST | `/api/library/{zotero\|mendeley}/sync` | Session | **202** enqueue `library_sync` job (+ `sync:true` inline) |
| POST | `/api/library/{zotero\|mendeley}/pull-pdfs` | Session | Pull PDFs from ref-mgr onto need_pdf stubs; enqueue `import` |
| POST | `/api/library/files/<id>/pull-pdf` | Session | Pull PDF for one stub from linked provider |
| GET | `/api/library/sync/runs`… | Session | Sync run history + poll by id |
| CRUD | `/api/library/collections`… | Session | Collections + membership |
| CRUD | `/api/writing/documents`… | Session | `WritingDocument` |
| POST | `/api/search` | Session | `SearchResult[]` |

## Frozen rules

1. EvidenceQuery **must not** include `prompt`, `model`, `temperature`, `embeddings`, `provider`, `api_key`.
2. Error body: `{ error, detail }` ([error-contract.md](../error-contract.md)).
3. RI responses use **`objects`**, not `items`.
4. Additive response fields only without ADR for renames/removals.
5. `file_id` / `paper_id` dual naming on EvidenceObject; prefer `file_id` in new code.

## Change process

ADR (if breaking) → update freeze pack → update this index → bump `contracts_version` → notify Developer B.
