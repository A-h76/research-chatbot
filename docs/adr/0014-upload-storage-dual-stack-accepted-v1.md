# ADR-0014: Accept upload/storage dual stacks for V1

Status: accepted (V1)  
Date: 2026-08-02  
Related: [#17 Upload + Worker](../audit/11-VERSION1-COMPLETION-TRACKER.md) ·
[`03-TECHNICAL-DEBT-REPORT.md`](../audit/03-TECHNICAL-DEBT-REPORT.md) ·
[`upload-architecture.md`](../upload-architecture.md)

## Context

The codebase has two storage façades and two upload HTTP surfaces:

| Concern | Stack A | Stack B |
|---------|---------|---------|
| Storage | root `storage/` (`StorageProvider`) | `backend/storage/` (`StorageBackend`) |
| Upload HTTP | Session `POST /api/files` (+ legacy paths) | JWT `backend/upload` (documents / bulk / presign) |

Both stacks enqueue the **same** Postgres `upload_jobs` / `worker.py` HANDLERS
chain (`import → phase1_analysis → paper_analysis`). Dualism is at the **entry**
and blob-provider layer, not a second queue.

Constitution Principle 1 forbids rewriting a working module without an ADR.
Unifying façades is desirable for long-term maintainability but is **not** a
Version-1 closed-beta exit criterion.

## Decision

**For V1 / closed beta: keep both stacks. Document them as known debt. Do not
unify storage or upload APIs in this milestone.**

Exit criteria for subsystem #17 are:

1. Canonical analysis path on the worker (`phase1_analysis`; legacy
   `extract_metadata` drained via redirect shim).
2. This ADR accepting dual-stack for V1.
3. Worker heartbeat / health smoke on the deploy checklist.

A later ADR may introduce a single façade and migrate callers gradually.

## Consequences

- Call sites must keep using the stack they already use (check before adding
  storage code — see `CLAUDE.md`).
- New features that need upload should prefer the JWT `backend/upload` path
  when adding Bearer clients; session SPA may keep `/api/files` until a unify ADR.
- Ops treat `GET /api/worker/health` as the single liveness signal for the
  shared worker, regardless of which upload API created the job.
