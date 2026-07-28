# ADR-0007: Freeze Evidence Query as the RI ask interface

Status: accepted  
Date: 2026-07-28

## Context

Phase 2.2 Evidence Platform is closed (`v0.2.0-rc1`). Phase 2.3 Research
Intelligence must compute over EvidenceObjects via one pipeline (ADR-0006).
Without a shared ask shape, Writing / Reviewer / Compare / Assistant will
each invent retrieval parameters (prompts, embeddings, ad hoc filters).

## Decision

Freeze **Evidence Query** (`EvidenceQuery`) as the universal interface for
requesting evidence. It is the query language of the Evidence Layer.

Contract fields (v0 — minimal):

- `intent`
- `scope`
- `filters`
- `ranking_strategy`
- `result_limit`

Optional presentation hints may include `query_text` and `anchors` without
becoming model/embedding controls.

**Explicitly not part of the platform contract:** `prompt`, `model`,
`temperature`, `embeddings`, `vector_index`, or any LLM provider knobs.

Canonical doc + fixtures:
`docs/architecture/phase-2.3-evidence-query-contract.md`,
`tests/fixtures/evidence/evidence_query_v0.json`.

Retrieval (Sprint 1) implements this contract; it does not redefine it.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Per-feature retrieval kwargs | Dual truth; no shared rank/consensus input |
| Bake embeddings into the query | Couples contract to one retrieval tech |
| Include model/prompt in query | Pulls NL generation into the ask layer |

## Consequences

- All RI consumers submit EvidenceQuery.
- Ranking strategy is a named version string, not inline weights.
- Changing the query shape requires a new ADR / contract version.

## Cost / Security / Observability / Extensibility

- **Cost:** One retrieval path amortizes work.  
- **Security:** `scope` carries tenant/project; server enforces ownership.  
- **Observability:** Log intent + strategy + counts — not full quotes by default.  
- **Extensibility:** New intents are additive enums; new filters are additive.
