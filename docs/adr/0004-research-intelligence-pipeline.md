# ADR-0004: Research Intelligence Pipeline binds all intelligent features

Status: accepted  
Date: 2026-07-28

## Context

ADR-0003 and the Week 2 Evidence Layer ADD freeze the **platform** (objects, provenance, bindings, explain, review). Principal review correctly notes that this is necessary but not sufficient: Dhund still needs a shared **intelligence** lifecycle so Writing, Reviewer, Compare, and Assistant do not each become a private GPT wrapper.

## Decision

Accept **ADD-0005** (`docs/architecture/add-0005-research-intelligence-pipeline.md`) as permanent architecture:

1. Platform (Evidence Layer) and Research Intelligence (capability pipeline) are distinct.
2. Every intelligent feature follows: Intent → Retrieval → Ranking → Consensus → Conflict → Reasoning → Natural Language → UI.
3. Natural language is last; consensus/conflict are structured aggregation first; no PDF/embedding bypass of the Evidence Layer for research claims.
4. Post–Week 2 capability sequence (retrieval → … → OS) guides roadmap; it does not expand Week 2 MVP scope.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Jump to AI writing after Week 2 | Generation without retrieval/rank/consensus recreates generic LLM tools |
| Per-feature private search/rank | Dual truth; breaks Inspector / Reviewer / Assistant consistency |
| LLM-first consensus/conflict | Invented narrative; violates Evidence First |
| Defer any intelligence ADD until Month 12 | Features will invent divergent pipelines in the gap |

## Consequences

- Phase 2.4 / 2.5 and future Assistant/Compare work inherit a single contract.
- Week 2 stays thin; Months 2+ add search/rank/consensus as explicit milestones.
- PRs that bypass the pipeline need a waiving ADR.

## Cost / Security / Observability / Extensibility

- **Cost:** Shared retrieval/rank amortizes model spend; generation called less often.
- **Security:** Same tenant rules as Evidence Layer; no new public evidence share by default.
- **Observability:** Pipeline stage traces become the audit unit for “why this answer.”
- **Extensibility:** New UI surfaces plug into stages rather than forking intelligence.
