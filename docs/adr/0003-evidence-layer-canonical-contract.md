# ADR-0003: Evidence Layer as canonical research knowledge contract

Status: accepted  
Date: 2026-07-28

## Context

Dhund’s differentiator is evidence-backed research work, not freeform AI writing.
Phase 1.5 (`evidence_grading`) and Phase 1.7 (`knowledge_graph`) already produce
structured quality and support/contradict signals. Writing Studio Shell (`v0.1.0`)
exists without sentence↔evidence binding. A six-engine “Evidence Engine” vision
is the long-term architecture, not the next sprint.

Without a hard rule, future AI features will bypass structured evidence and
become generic GPT wrappers.

## Decision

1. **Ship Phase 2.2 as an Evidence Layer MVP**, not six independently deployed engines.
2. **`EvidenceObject` is the canonical unit** of research knowledge in Dhund.
   Claims, findings, and results are fields or views of EvidenceObject — not
   competing root entities.
3. **Week 2 freezes:** Evidence Objects, provenance, sentence bindings, Evidence
   Inspector, candidate status, human review (`claim_reviews` / evidence reviews),
   versioned extraction, and `POST /api/evidence/explain`.
4. **Reuse Phase 1.1 / 1.5 / 1.7** for anchors, quality, and support/contradict
   signals. Do not build a parallel quality scorer or graph store.
5. **Constitution Principle 11 (Evidence First)** binds all future AI features to
   consume this layer rather than bypass it.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Implement six engines in Week 2 | Confuses final architecture with next sprint; delays invites |
| New `papers` table | Duplicates Library `files` / Research Ready identity |
| LLM-first explain without stored objects | Invents evidence; violates trust model |
| Absolute immutability of extracts | Blocks pipeline bugfixes; use append-only versions instead |

## Consequences

- Writing Inspector, later Reasoning, Reviewer, and Compare all share one object model.
- Extraction must be page-anchored and project-scoped.
- Guided generation (2.4) is blocked until Evidence Layer is proven.

## Cost / Security / Observability / Extensibility

- **Cost:** Extraction is async worker work; rate-limited; Research Ready gated.
- **Security:** `user_id` + `project_id` ownership; validate evidence ids server-side.
- **Observability:** Provenance + pipeline_version on every object; review audit log.
- **Extensibility:** `backend/evidence/` modular monolith seam; engines may split later.
