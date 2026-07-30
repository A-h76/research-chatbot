# A-402 — Frontend Compatibility Notes

**Status:** Frozen (A-402)  
**Audience:** Developer B  
**contracts_version:** `1.2.0`  
**Code mirrors:** `frontend/src/features/evidence/api.ts`, `useGroundedWriting`, `apiClient`

---

## 1. Do / don’t

| Do | Don’t |
|----|--------|
| Expect **flat** JSON bodies | Unwrap `response.data` as an API envelope (React Query’s `.data` is fine — that’s the HTTP body) |
| Use RI `objects` | Expect RI `items` |
| Use list endpoints’ `items` | Mix list/`objects` keys |
| Read `writing` from RI writing responses | Treat writing fields as top-level-only |
| Use citation `evidence_id` | Use `evidence_object_id` on writing citations |
| Handle writing `status: "blocked"` on HTTP 200 | Treat blocked as HTTP error |
| Ignore unknown fields | Fail closed on additive keys |
| Prefer `file_id`; accept `paper_id` as alias | Require only one name without fallback |

---

## 2. Error handling

```ts
// Matches apiClient today
const message = body.detail || body.error || "Request failed";
```

Branch:

- `422` → validation  
- `404` → missing / inaccessible  
- `409` → extract conflict  
- `429` → backoff  

---

## 3. EvidenceQuery pitfalls

- Valid **intents** only (see api-contracts).  
- `literature_review` → set **`section_type`**, not `intent`.  
- Never send `model` / `prompt` / `temperature` / provider knobs.  
- Body may be bare query or `{ query: {…} }`.

---

## 4. Writing UI

```ts
const writing = raw.writing; // required nest
if (writing?.status === "blocked") { /* calm empty / CTA */ }
const runId = writing?.reviewer_run_id; // optional; present when document scoped
```

Reviewer history:

- `GET /api/documents/{id}/reviewer-runs/latest` for accordion  
- Prefer reconstructed `review` + `findings` over re-running writing solely for display  

---

## 5. Type drift to fix over time (non-blocking for A-402)

IDD-0004 / older sketches may still show flat `GroundedWritingResult` or review `action` fields.  
**Implement against this freeze + live `evidence/api.ts`**, then align `frontend/src/types` in a follow-up (B ticket).

---

## 6. Compatibility checklist before merging FE against these APIs

- [ ] RI stages type `objects`, `stage`, `timing_ms?`, `versions?`  
- [ ] Writing unwraps `raw.writing`  
- [ ] Citations use `evidence_id`  
- [ ] Extract handles 202 / 200 / 400 / 409  
- [ ] Errors use `detail || error`  
- [ ] No dependency on undocumented IDD-only field names
