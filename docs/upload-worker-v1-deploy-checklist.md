# Upload + Worker V1 — deploy checklist

**Subsystem:** #17  
**Companions:** [`ADR-0014`](./adr/0014-upload-storage-dual-stack-accepted-v1.md) ·
[`v1-beta-rollout.md`](./v1-beta-rollout.md) · [`auth-v1-deploy-checklist.md`](./auth-v1-deploy-checklist.md)

---

## 1. Worker process + heartbeat

| Check | Expected |
|-------|----------|
| `python worker.py` (or Procfile/worker service) | Running against **Postgres** (not SQLite) |
| `GET /api/worker/health` | `200` + `"status": "ok"` when heartbeat age ≤ threshold |
| Fresh deploy, worker not started | `503` + `"status": "unknown"` or `"down"` |

Automated coverage: `pytest test_worker_health.py -v` (writes heartbeat via
`worker._heartbeat()`, asserts health route).

Ops smoke after deploy:

```bash
curl -sS "$APP_BASE_URL/api/worker/health"
# expect: {"status":"ok","age_seconds":..., ...}
```

If `unknown`/`down`: start/restart the worker service; confirm `DATABASE_URL`
matches the web process.

---

## 2. Canonical job chain

New uploads should produce:

`import` → `phase1_analysis` → `paper_analysis` (all `done`).

Legacy `extract_metadata` rows (if any) are handled by a **drain shim**: the
worker marks them complete and enqueues `phase1_analysis` (no LLM). Optional
ops query:

```sql
SELECT id, status, file_id, created_at
FROM upload_jobs
WHERE job_type = 'extract_metadata'
  AND status IN ('pending', 'running', 'failed')
ORDER BY id DESC
LIMIT 50;
```

After the worker polls, pending legacy rows should clear; new jobs must not
be `extract_metadata`.

---

## 3. Dual-stack note (accepted for V1)

Session `/api/files` and JWT `backend/upload` both feed the same worker.
Do **not** block deploy on unifying `storage/` vs `backend/storage/` —
see ADR-0014.

---

## 4. Metrics (optional but recommended)

| Probe | Notes |
|-------|--------|
| Flask `/metrics` | Token or loopback per deploy hardening |
| Worker metrics port | `worker.py` may expose its own Prometheus endpoint |

Smoke: scrape once after a successful upload → job completion cycle.
