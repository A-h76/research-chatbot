# TECHNICAL_DEBT — Register

**Last updated:** 2026-07-28  
**Rule:** Debt here is intentional or deferred — not an invitation to rewrite without an ADR (`docs/00-constitution.md`).

---

## High

| Item | Why it exists | Resolution direction |
|------|---------------|----------------------|
| `server.py` monolith (~6.8k+ lines) | Historical single entrypoint; owns models | Extract blueprints/services gradually; keep factory/DI |
| Dual upload APIs + dual storage facades (`storage/` vs `backend/storage/`) | Two consumers evolved separately | Unify behind one storage + validation policy |
| Chat vs Prompt Engine divergence | Legacy chat path predates PromptBuilder | Finish chat migration; don’t fork a third path |
| Dual cost ledgers | Legacy + Prompt Engine attribution | Consolidate |

---

## Medium

| Item | Why it exists | Resolution direction |
|------|---------------|----------------------|
| Legacy confirm-upload / thread analysis paths | Older product flows | Route all analysis through AnalysisPipelineService + worker |
| `extract_metadata` LLM job still in HANDLERS | **Drain shim #17** (→ phase1) | Drop HANDLER after zero pending in prod |
| `feature_flags` / unused `import_sessions` / `search_index` gaps | Schema ahead of product | Implement or drop |
| Worker LLM overview vs Phase 1.6 AssembledPrompt unused by chat | Parallel product bets | Pick one research-prompt path |
| `PipelineVersion` not on live Base | Migration/ORM drift | Register or remove FK usage |
| ORM vs migration type drift | Incremental schema | Align types; prefer BigInteger for bytes |
| Missing FK indexes on hot chat paths | Early schema | Add migrations |
| Branding: Personal AI / Soro / ResearchOS / Dhund | Rename in progress | Prefer **Dhund** in new user-facing copy |
| Obsolete docs claiming “not implemented” / “no CI” | Stale | Mark superseded; point to Dhund-Flow |

---

## Low

| Item | Resolution |
|------|------------|
| Unused `get_current_user` / `jwt_optional` helpers | Use or remove |
| CI `SECRET_KEY` vs `FLASK_SECRET_KEY` naming | Align env |
| Writing page raw fetch vs shared `writingApi` | Prefer shared client |
| Dead frontend leftovers | Continue hygiene PRs |

---

## Explicitly not “debt to rewrite”

| Area | Stance |
|------|--------|
| Postgres SKIP LOCKED queue (not Celery) | ADR-0001 — extend handlers, don’t replace wholesale |
| Evidence Platform contracts | Frozen — ADR to change |
| Analysis Phase 1 engines | Feed Evidence; don’t replace with LLM-as-knowledge |
| SQLite for local API-only | OK for boot; never claim worker-capable |

---

## Related

- Constitution: `docs/00-constitution.md`  
- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)  
- [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md)
