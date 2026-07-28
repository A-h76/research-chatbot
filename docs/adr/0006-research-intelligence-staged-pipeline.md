# ADR-0006: Research Intelligence is a staged pipeline over Evidence Queries

Status: accepted (binds Phase 2.3 design; implementation starts after `v0.2.0-rc1`)  
Date: 2026-07-28

## Context

Phase 2.2 freezes the Evidence Layer (ADR-0003, ADR-0005). Phase 2.3
(ADD-0005) must add intelligence without forking knowledge storage or
spawning five independent “engines” that each invent retrieval.

## Decision

1. **Research Intelligence is one pipeline**, not independent modules.
   Stages, in order:

   ```text
   Evidence Layer
        → Retrieval → Ranking → Consensus → Conflict → Reasoning → Presentation
   ```

   Each stage has exactly: one responsibility, one API, one test suite, one contract.

2. **Evidence Query is the universal ask interface** (frozen before
   Retrieval implementation). Writing, Reviewer, Compare, and Research
   Assistant submit the same Evidence Query shape — the “SQL” of the
   Evidence Layer.

3. **Research Intelligence never owns knowledge.** It only computes over
   Evidence Layer objects:
   - Retrieval **returns** EvidenceObjects  
   - Ranking **reorders** EvidenceObjects  
   - Consensus **aggregates** EvidenceObjects  
   - Conflict **links** EvidenceObjects  
   - Reasoning **explains** EvidenceObjects  

   No stage creates a second representation of the research corpus.

4. **No further architecture docs are required before `v0.2.0-rc1`.**
   After RC tag: close Phase 2.2, open Phase 2.3 at Retrieval (after
   Evidence Query contract freeze in the 2.3 kickoff).

Canonical detail: `docs/architecture/phase-2.3-research-intelligence-pipeline.md`
and Evidence Query section therein / ADD-0005 updates.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Five deployable engines on day one | Premature independence; dual contracts |
| Per-feature custom retrieval | Dual truth; breaks Inspector/Reviewer consistency |
| RI-owned claim/graph store | Violates Evidence Layer freeze |
| More ADDs before RC | Delays stable substrate; architecture is sufficient |

## Consequences

- Phase 2.3 Sprint 0 (design): freeze Evidence Query contract.  
- Sprint 1: Retrieval implementing that query.  
- Later stages compose; Presentation is Writing/Reviewer/Compare/Assistant.

## Cost / Security / Observability / Extensibility

- **Cost:** Shared query amortizes retrieval.  
- **Security:** Same tenant rules as Evidence Layer; query scoped by project/user.  
- **Observability:** Pipeline stage traces on each Evidence Query.  
- **Extensibility:** New UIs submit queries; they do not fork stages.
