# Now-Status — Dhund Architecture Review Pack

**Date:** 2026-07-30  
**Role:** Principal Software Architect — Phase 0 review  
**Scope:** Full codebase (Flask modular monolith + React SPA + Postgres worker)  
**Stance:** Evolve existing architecture. Do not rewrite well-designed seams.

## Documents in this folder

| File | Contents |
|------|----------|
| [01-ARCHITECTURE-ASSESSMENT.md](./01-ARCHITECTURE-ASSESSMENT.md) | Strengths, weaknesses, missing foundation, reuse plan, scorecard, PE join answer |
| [02-DEPENDENCY-GRAPH.md](./02-DEPENDENCY-GRAPH.md) | Layer graph, blueprint map, circular / dual-stack risks |
| [03-DOMAIN-COVERAGE.md](./03-DOMAIN-COVERAGE.md) | Vision vs current: ✅ / 🟡 / ❌ |
| [04-IDD.md](./04-IDD.md) | Interface Definition Document — natural next version of existing contracts |
| [05-MIGRATION-ROADMAP.md](./05-MIGRATION-ROADMAP.md) | Phase 1 (no break) → Phase 2 (extend) → Phase 3 (future) |

## Non-negotiables discovered in review

1. **No Prisma / Drizzle** — SQLAlchemy + raw SQL migrations only.
2. **`EvidenceObject` is the canonical knowledge unit** (ADR-0003) — do not invent a parallel `papers` / Claim root entity.
3. **Postgres worker stays** (ADR-0001) — do not migrate to Celery without a new ADR.
4. **Never `import server` from packages loaded by `server.py`** — factory / DI pattern.
5. **Marketing site ≠ Application** — Jinja (`/`, `/product`, …) vs SPA (authenticated `/`).

## One-line verdict

Dhund already has a credible Research OS spine (Library → Evidence → Writing → Verify). The highest-leverage work is **consolidation and contract documentation**, not a greenfield redesign.
