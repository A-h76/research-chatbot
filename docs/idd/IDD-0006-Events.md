# IDD-0006 — Events

| Field | Value |
|-------|-------|
| **Status** | Active (catalog aligned with living event contracts) |
| **Transport today** | Postgres `outbox_events` + `upload_jobs` status (no mandatory Kafka) |
| **Future** | Same payloads may fan-out to webhook/bus without changing shape |

Events enable Frontend polling, worker chaining, and future projections **without** coupling to LLM internals.

---

## 1. Envelope

```json
{
  "event_id": "uuid-or-int",
  "type": "EvidenceCreated",
  "occurred_at": "2026-07-30T12:00:00Z",
  "producer": "worker.evidence_extract",
  "aggregate_type": "evidence_object",
  "aggregate_id": 123,
  "payload": {},
  "schema_version": 1
}
```

---

## 2. Event catalog

### PaperUploaded

| | |
|--|--|
| **Payload** | `{ paper_id, user_id, project_id?, source, filename }` |
| **Producer** | Upload API |
| **Consumer** | Worker (`import` job), Frontend (library invalidate) |
| **Retry** | Outbox until dispatched; upload job retries with backoff |

### PaperProcessed

| | |
|--|--|
| **Payload** | `{ paper_id, research_readiness, pipeline_version?, job_id }` |
| **Producer** | Worker after import / phase1 |
| **Consumer** | Frontend pipeline UI; may enqueue `evidence_extract` only on user action |
| **Retry** | Job attempts → `failed` dead-letter |

### EvidenceExtractionStarted

| | |
|--|--|
| **Payload** | `{ run_id, project_id, paper_id, job_id }` |
| **Producer** | Evidence extract API / worker |
| **Consumer** | Frontend progress stages |
| **Retry** | Job-level |

### EvidenceCreated

| | |
|--|--|
| **Payload** | `{ evidence_object_id, project_id, paper_id, status: "candidate" }` |
| **Producer** | Evidence extractor |
| **Consumer** | Frontend evidence lists; KG projection (future) |
| **Retry** | Idempotent on `content_hash` |

### EvidenceUpdated

| | |
|--|--|
| **Payload** | `{ evidence_object_id, status, supersedes_id? }` |
| **Producer** | Review API (accept/reject/edit) |
| **Consumer** | Inspector, Writing evidence rail |
| **Retry** | Sync HTTP; outbox optional |

### WritingGenerated

| | |
|--|--|
| **Payload** | `{ document_id, project_id, writing_version, status: "ok"|"blocked" }` |
| **Producer** | Writing intelligence service |
| **Consumer** | Writing UI; analytics |
| **Retry** | Request-scoped; client may retry POST |

### ReviewCompleted

| | |
|--|--|
| **Payload** | `{ document_id, reviewer_version, issue_count, metrics, status?, reviewer_run_id? }` |
| **Producer** | Reviewer persistence on grounded writing (when `document_id` scoped) |
| **Consumer** | Reviewer accordion; export gate |
| **Retry** | Request-scoped persist; outbox record for downstream |

`reviewer_run_id` is present when a durable `reviewer_runs` row was written (A-401).

### ExportFinished

| | |
|--|--|
| **Payload** | `{ export_job_id, document_id, format, status, download_url? }` |
| **Producer** | Export service |
| **Consumer** | Export UI download |
| **Retry** | Job retries; user-visible failure after max attempts |

### BindingCreated / BindingDeleted

| | |
|--|--|
| **Payload** | `{ binding_id, document_id, evidence_object_id }` |
| **Producer** | Bindings API |
| **Consumer** | Export provenance, confidence metrics |
| **Retry** | Sync |

---

## 3. Delivery & retry strategy

| Path | Strategy |
|------|----------|
| HTTP request/response | No event bus; return DTO |
| Heavy work | `upload_jobs`: exponential/linear backoff; max attempts → `failed` |
| Outbox | Write event in same transaction as job create; mark `dispatched` when safe |
| Frontend | Poll `JobStatus` or invalidate React Query on mutation success |
| At-least-once | Consumers **idempotent** on aggregate + version/hash |

---

## 4. Frontend subscription model (v1)

No WebSocket required for v1:

1. After mutating API → invalidate queries.
2. While `JobStatus` in `pending|running` → poll 1–2s.
3. Optional future: SSE `GET /api/events/stream` carrying the same envelope—**additive**.

---

## 5. Naming rules

- Past tense, PascalCase type names.
- Payload fields snake_case.
- Never put raw PDF bytes or prompts in event payloads.
