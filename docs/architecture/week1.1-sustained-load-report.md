# Week 1.1 Sustained Load Report

Generated: `2026-07-30T08:59:01.210925+00:00`
Scope: Writing Studio Shell API (`/api/writing/documents*`)
Environment: Flask test client (local SQLite via root conftest)

## Budgets

- Stage 4 smoke (single-shot): < 500ms (see `tests/test_writing_performance.py`)
- Week 1.1 sustained p95: < 1500ms per operation class
- Week 1.1 sustained max: < 3000ms

## Results

### Burst autosave (n=40)

- Notes: Sequential content-changing autosaves on one document; version advanced each save.
- Stats: `{"error_count": 0, "max_ms": 11.68, "mean_ms": 8.81, "n": 40, "p50_ms": 8.85, "p95_ms": 10.34}`

### Cohort list p95

- Notes: 25× list documents
- Stats: `{"error_count": 0, "max_ms": 4.0, "mean_ms": 3.45, "n": 25, "p50_ms": 3.42, "p95_ms": 3.83}`

### Cohort open p95

- Notes: 25× open document
- Stats: `{"error_count": 0, "max_ms": 9.02, "mean_ms": 7.01, "n": 25, "p50_ms": 6.96, "p95_ms": 8.28}`

### Cohort autosave p95

- Notes: 25× autosave after list/open
- Stats: `{"error_count": 0, "max_ms": 10.37, "mean_ms": 9.07, "n": 25, "p50_ms": 9.17, "p95_ms": 10.02}`

### Conflict storm (stale version ×20)

- Notes: All requests must return 409 version_conflict after head advances.
- Stats: `{"conflict_count": 20, "error_count": 0, "max_ms": 10.5, "mean_ms": 6.56, "n": 20, "p50_ms": 6.08, "p95_ms": 10.13}`

## Bottleneck notes

- Measurements are process-local Flask test-client latencies, not production network RTT.
- Rate limit on autosave is `120/hour` — burst profile sized under that ceiling.
- Remediation priority if p95 breaches: document open query path, autosave version row insert, activity logging.

## Gate

- [x] Sustained suite present (`tests/test_writing_sustained_load.py`)
- [x] Report artifact path reserved for Week 1.1 evidence pack

