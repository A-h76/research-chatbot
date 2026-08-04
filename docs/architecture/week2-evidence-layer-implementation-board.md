# Week 2 Evidence Layer Implementation Board

Status: Planned (docs frozen — implementation not started)  
Source plans:

- `docs/architecture/week2-evidence-layer-architecture.md` (ADD)
- `docs/architecture/week2-evidence-layer-backend-technical-design.md`
- `docs/architecture/week2-evidence-layer-frontend-technical-design.md`
- `docs/architecture/week2-evidence-layer-verification-and-qa-spec.md`
- ADR-0003, Constitution Principle 11
- Migration: `migrations/0033_evidence_layer.sql`

---

## How to use

- Treat each slice as a mini sprint.
- Do not start the next slice until current gates are green.
- Keep backend/frontend synchronized via contract fixtures.
- Every slice: implement → review → verification gate.


## Status vocabulary

Slice: `Not Started` | `In Progress` | `In Review` | `Verified` | `Done` | `Blocked`  
Milestone: `Planned` | `Active` | `Complete` | `Pending Approval` | `Released`

---

## Milestone

| Milestone | Status |
|-----------|--------|
| Week 2 Evidence Layer MVP (Phase 2.2) | Planned |
| Target RC tag (when ready) | `v0.2.0-rc1` (provisional) |

---

## Foundation and governance

- [x] **Design freeze** — ADD + ADR-0003 + Principle 11 + backend/frontend TDS + QA  
  Status: Done  
  Gates: Principle 0 binding; non-goals listed; reuse of 1.5/1.7 explicit

- [ ] **Execution setup**  
  Owner: Eng leads  
  Status: Not Started  
  Gates: DoR/DoD; branch/PR rules; contract fixture path `tests/fixtures/evidence/`

---

## Backend slices

- [ ] **BE-0 — Package foundation**  
  Status: Not Started  
  Work: `backend/evidence/` modules, DI container, errors/logging  
  Gates: importable without `import server`; unit smoke

- [ ] **BE-A — Schema**  
  Depends: BE-0  
  Work: apply `0033`; SQLAlchemy models wired in `server.py`; indexes verified  
  Gates: migration on Postgres; SQLite-safe app enforcement for partial unique

- [ ] **BE-B — Objects + scoring + provenance**  
  Depends: BE-A  
  Work: serializers, `confidence_band`, content_hash, supersede helper  
  Gates: unit tests for bands + hash stability

- [ ] **BE-C — Extraction job**  
  Depends: BE-B  
  Work: Research Ready gate; worker handler; idempotent runs; candidate-only  
  Gates: ready vs not-ready; idempotency; partial failure

- [ ] **BE-D — Reviews + bindings**  
  Depends: BE-B  
  Work: review transitions; sentence bindings CRUD; authz  
  Gates: IDOR negatives; accept/reject/edit audit

- [ ] **BE-E — Explain API**  
  Depends: BE-D  
  Work: `POST /api/evidence/explain`; sufficiency; chain from stored data  
  Gates: insufficient empty; no invented ids; contract fixtures

---

## Frontend slices

- [ ] **FE-0 — Types + API + mappers**  
  Status: Not Started  
  Work: `features/evidence/` client + fixtures  
  Gates: mapper tests green

- [ ] **FE-A — Evidence Inspector panel**  
  Depends: FE-0, BE-E contract  
  Work: panel UI; sufficiency; cards; candidate labels  
  Gates: sufficient/weak/insufficient stories

- [ ] **FE-B — Editor selection integration**  
  Depends: FE-A  
  Work: block_id / range → debounced explain; sticky selection  
  Gates: no client re-rank; a11y live region

- [ ] **FE-C — Optional review/bind affordances**  
  Depends: FE-B, BE-D  
  Work: link evidence; accept/reject if in MVP UI  
  Gates: authz errors surfaced

---

## Cross-cutting / Stage 4

- [ ] **Security matrix** — IDOR, untrusted PDF text, rate limits  
- [ ] **Perf smoke** — explain + extract measured  
- [ ] **a11y pass** — Inspector keyboard + live region  
- [ ] **Stage 4 evidence note** — `docs/architecture/week2-evidence-layer-stage4-evidence.md`  
- [ ] **RC decision** — Pending Approval → tag when signed

---

## Hard bans (do not schedule in Week 2)

- Reasoning Engine chat
- Research memory
- Guided generation (2.4)
- Citation engine rebuild (2.3)
- Neo4j / six deployable engines
- New `papers` table

---

## Dependency graph

```text
Design freeze ✓
  -> Execution setup
  -> BE-0 -> BE-A -> BE-B -> BE-C
                 \-> BE-D -> BE-E
  -> FE-0 -> FE-A -> FE-B -> FE-C
  -> Stage 4 -> RC
```
