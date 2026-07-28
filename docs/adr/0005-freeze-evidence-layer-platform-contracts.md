# ADR-0005: Freeze Evidence Layer platform contracts (v0.2.0)

Status: accepted  
Date: 2026-07-28

## Context

Phase 2.2 Evidence Layer is implemented and Stage 4 automated gates are green.
Research Intelligence (Phase 2.3) will build on this substrate. Without a
hard freeze, RI work will casually reshape EvidenceObject / explain /
bindings and recreate dual truth.

## Decision

The following are **frozen platform contracts** as of Evidence Layer RC
(`v0.2.0-rc1` target):

1. `EvidenceObject` shape and semantics  
2. `POST /api/evidence/explain` request/response contract  
3. Sentence / writing bindings model  
4. Review workflow (`candidate` → `accepted` | `rejected` | edited-via-supersede)  
5. Provenance model (`provenance_json` + `pipeline_version` + `content_hash`)  
6. Confidence bands (`low` | `moderate` | `high` only in public API)

Any breaking change requires a new ADR (and usually a contract version bump).
Additive, backward-compatible fields may ship with fixture updates in the
same change set.

Canonical freeze doc: `docs/architecture/week2-evidence-layer-platform-contracts.md`.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Keep contracts “soft” until 2.3 | RI will fork shapes; Inspector and extract diverge |
| Freeze only HTTP routes | ORM/domain semantics still drift |
| Version every additive field | Unnecessary ceremony; freeze breaks only |

## Consequences

- Phase 2.3 must consume these contracts, not replace them.
- Explain / bindings / reviews remain the Writing Inspector path.
- New retrieval APIs (`/search`, `/retrieve`) are **additive** under Research Intelligence — they must return or reference frozen EvidenceObjects.

## Cost / Security / Observability / Extensibility

- **Cost:** Low — documentation + fixture discipline.  
- **Security:** Ownership rules on frozen routes stay release blockers.  
- **Observability:** `pipeline_version` + provenance remain audit keys.  
- **Extensibility:** RI adds APIs beside the freeze; does not mutate accepted objects in place.
