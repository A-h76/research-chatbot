# Now-Status — Dhund Architecture Review Pack

**Date:** 2026-07-30  
**Role:** Principal Software Architect — Phase 0 review → Foundation freeze complete  
**Scope:** Full codebase (Flask modular monolith + React SPA + Postgres worker)  
**Stance:** Evolve existing architecture. Do not rewrite well-designed seams.

## Documents in this folder

| File | Contents |
|------|----------|
| [01-ARCHITECTURE-ASSESSMENT.md](./01-ARCHITECTURE-ASSESSMENT.md) | Strengths, weaknesses, missing foundation, reuse plan, scorecard |
| [02-DEPENDENCY-GRAPH.md](./02-DEPENDENCY-GRAPH.md) | Layer graph, blueprint map, circular / dual-stack risks |
| [03-DOMAIN-COVERAGE.md](./03-DOMAIN-COVERAGE.md) | Vision vs current |
| [04-IDD.md](./04-IDD.md) | Interface Definition Document notes |
| [05-MIGRATION-ROADMAP.md](./05-MIGRATION-ROADMAP.md) | Historical *architecture* consolidation phases (not product Phase 2) |

## Next product chapter

| Doc | Contents |
|-----|----------|
| [PHASE-2-RESEARCH-INTELLIGENCE.md](../docs/roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md) | **Phase 2 — Research Intelligence** (RI-001…009, capability map, 60/20/10/10) |
| [EPIC-0006](../docs/epics/EPIC-0006-Research-Intelligence.md) | Active epic |
| [A-405 freeze](../docs/contracts/A-405-documentation-freeze.md) | Platform contracts locked |

## Non-negotiables

1. **No Prisma / Drizzle** — SQLAlchemy + raw SQL migrations only.
2. **`EvidenceObject` is the canonical knowledge unit** (ADR-0003).
3. **Postgres worker stays** (ADR-0001).
4. **Never `import server` from packages loaded by `server.py`**.
5. **Marketing site ≠ Application**.
6. **Architecture evolves on product demand** — no six-month polish while RI waits.

## One-line verdict

Foundation is **good enough**. Highest leverage now is **Research Intelligence** (themes, matrix, consensus/contradiction WHY, gaps, graph)—not another internals refactor.
