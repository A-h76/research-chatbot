# Week 2 Evidence Layer — Extraction Job Spec

Status: Frozen (detail for BE-C)  
Parent: `docs/architecture/week2-evidence-layer-backend-technical-design.md` §4

---

## Purpose

Create **candidate** `EvidenceObject` rows from Research Ready library files by projecting Phase 1.1 / 1.5 / 1.7 outputs into the canonical schema. Never invent quotes, pages, or evidence ids.

---

## Preconditions

| Check | On failure |
|-------|------------|
| Authenticated owner / project membership | Reject enqueue |
| `file_id` exists and tenant-owned | 404/403 |
| File is **Research Ready** | Run `skipped` |
| Phase 1 artifacts available (DU + optional EG/KG) | `failed` retryable or `skipped` with reason |
| Quota / rate limit | 429 |

---

## Identity and idempotency

```text
input_content_hash = H(
  file_content_fingerprint,
  document_understanding_version,
  evidence_grading_version,
  knowledge_graph_version,
  extraction_prompt_version,
  pipeline_version
)

object content_hash = H(
  file_id, page, char_start, char_end, normalized_quote, normalized_claim
)
```

Unique extraction run: `(project_id, file_id, pipeline_version, input_content_hash)`.

If succeeded run exists and `force=false` → return prior counts; create no duplicates.

Active object uniqueness: `(project_id, file_id, content_hash, pipeline_version)` where status ∉ {superseded, rejected}.

---

## Candidate vs accepted

| Stage | Status |
|-------|--------|
| Fresh extract | `candidate` only |
| Human accept | `accepted` (+ `claim_reviews` row) |
| Human reject | `rejected` |
| Re-extract newer pipeline/hash | new `candidate`; prior → `superseded` |

Extraction **must not** auto-accept.

---

## Page anchoring (required)

Every inserted object MUST have:

- `file_id`
- `quote` (non-empty)
- `page` when available from DU; if page unknown, record provenance gap and **do not** claim a fake page — prefer skip candidate over ungounded claim

Prefer `char_start` / `char_end` when DU provides spans. Free-floating “ideas” without quote are rejected by validator.

---

## Mapping from Phase 1

| Source | Target fields |
|--------|---------------|
| DU sections / spans | `section`, `page`, `quote`, char offsets |
| EG grades | `study_quality`, inputs to `confidence_band` |
| KG `EVIDENCE_CLAIM` nodes | `claim`, optional `source_kg_node_id` |
| KG `SUPPORTS` / `CONTRADICTS` | `supports_json` / `contradicts_json` |
| Study design heuristics | `study_type` |

Scoring v0: ordinal `low|moderate|high` only — see backend TDS §5.

---

## Versioning / supersede

1. Insert new rows for new hash/version.
2. Set `supersedes_id` to prior object when replacing same logical span/claim.
3. Mark prior `status=superseded`.
4. Never silently rewrite `quote`/`claim` on an `accepted` row — accept path edits create superseding version via reviews service.

---

## Partial failure

- Per-candidate validation errors are logged and skipped.
- Run succeeds if completed with `objects_created >= 0` and no fatal I/O — empty valid extract (no claims in paper) is success with zero objects.
- Project aggregates must ignore failed files.

---

## Security

- Paper text = untrusted input.
- Structured schema validation on model/extractor output.
- Strip/ignore instruction-like strings in claim fields.
- Do not log full quotes at info level.

---

## Worker payload

```json
{
  "user_id": 1,
  "project_id": 2,
  "file_id": 10,
  "pipeline_version": "2.2.0",
  "force": false
}
```

Handler registration: `worker.py` `HANDLERS["evidence_extract"]` → `backend.evidence.extractor` entrypoint via factory deps.
