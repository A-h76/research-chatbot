# A-404 — Job Observability Contract

**Status:** Shipped (additive)  
**contracts_version note:** Does not bump Evidence freeze; jobs are a platform surface.  
**Route:** `GET /api/jobs/{job_id}/status`  
**Code:** `backend/jobs/observability.py`

## Compatibility

| Keep | Additive |
|------|----------|
| `job_id`, `status`, `job_type`, `attempts`, `last_error`, `progress`, `updated_at`, `cached` | `lifecycle`, `retry`, `timings`, `error`, `file_id`, `max_attempts` |

`status` enum unchanged: `pending` \| `running` \| `done` \| `failed`.

## Lifecycle (derived)

| lifecycle | When |
|-----------|------|
| `queued` | pending, attempts=0, due |
| `scheduled` | pending, attempts=0, run_after in future |
| `retry_wait` | pending, attempts>0 |
| `running` | running |
| `succeeded` | done |
| `dead_letter` | failed |

## Metrics (Prometheus / worker)

- `upload_jobs_completed_total{job_type,outcome}`
- `upload_job_retries_total{job_type}`
- `upload_job_duration_seconds{job_type,outcome}`

## Redis cache

Hash includes `payload_json` with the full status body so cache hits retain attempts / last_error / diagnostics.
