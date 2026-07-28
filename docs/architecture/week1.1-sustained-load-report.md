# Week 1.1 Sustained Load Report

Generated: `2026-07-28T10:44:20.832560+00:00`
Scope: Writing Studio Shell API (`/api/writing/documents*`)
Environment: Flask test client (local SQLite via root conftest)

## Budgets

- Stage 4 smoke (single-shot): < 500ms (see `tests/test_writing_performance.py`)
- Week 1.1 sustained p95: < 1500ms per operation class
- Week 1.1 sustained max: < 3000ms

## Results

### Burst autosave (n=40)

- Notes: Sequential content-changing autosaves on one document; version advanced each save.
- Stats: `{"error_count": 0, "max_ms": 29.18, "mean_ms": 12.51, "n": 40, "p50_ms": 11.98, "p95_ms": 15.03}`

### Cohort list p95

- Notes: 25× list documents
- Stats: `{"error_count": 0, "max_ms": 10.23, "mean_ms": 5.39, "n": 25, "p50_ms": 4.61, "p95_ms": 9.11}`

### Cohort open p95

- Notes: 25× open document
- Stats: `{"error_count": 0, "max_ms": 13.33, "mean_ms": 9.85, "n": 25, "p50_ms": 9.72, "p95_ms": 12.1}`

### Cohort autosave p95

- Notes: 25× autosave after list/open
- Stats: `{"error_count": 0, "max_ms": 21.19, "mean_ms": 12.55, "n": 25, "p50_ms": 12.16, "p95_ms": 17.33}`

### Conflict storm (stale version ×20)

- Notes: All requests must return 409 version_conflict after head advances.
- Stats: `{"conflict_count": 20, "error_count": 0, "max_ms": 10.0, "mean_ms": 7.38, "n": 20, "p50_ms": 7.49, "p95_ms": 9.19}`

## Bottleneck notes

- Measurements are process-local Flask test-client latencies, not production network RTT.
- Rate limit on autosave is `120/hour` — burst profile sized under that ceiling.
- Remediation priority if p95 breaches: document open query path, autosave version row insert, activity logging.

## Gate

- [x] Sustained suite present (`tests/test_writing_sustained_load.py`)
- [x] Report artifact path reserved for Week 1.1 evidence pack

