# ADD-0005: Research Intelligence Pipeline

Status: Accepted (permanent capability architecture)  
Date: 2026-07-28  
Audience: Principal / staff engineers; product; anyone adding an “AI” surface  
Depends on: ADR-0003 (Evidence Layer), Constitution Principle 11, Week 2 Evidence Layer ADD  
Companion ADR: `docs/adr/0004-research-intelligence-pipeline.md`

---

## 1) The distinction this ADD freezes

Week 2 designs the **platform**:

```text
Library → Phase 1 Analysis → Evidence Layer → Writing Inspector
```

That solves storage, provenance, extraction, versioning, review, bindings, security, and explainability.

It does **not** yet design the **intelligence**.

| Layer | Job | Week 2 |
|-------|-----|--------|
| **Evidence Layer (platform)** | Hold grounded, auditable research knowledge | In scope |
| **Research Intelligence (capability)** | Retrieve, rank, aggregate, conflict-code, then optionally reason / narrate | **Out of Week 2** — this ADD |

> You've designed the platform. You haven't yet designed the intelligence.

Those are different things. Confusing them produces either (a) premature GPT wrappers on raw PDFs, or (b) endless storage work with no researcher-facing judgment.

**Research Intelligence is not another backend package.** It is a **capability lifecycle** every intelligent feature must follow. Modules (Writing, Reviewer, Compare, Assistant) are consumers of the pipeline, not alternate pipelines.

---

## 2) Binding lifecycle (no exceptions)

Every intelligent feature — Writing generation, Reviewer, Compare, Research Assistant, Gap Finder, and future surfaces — MUST follow this order:

```text
Intent
  ↓
Evidence Retrieval
  ↓
Evidence Ranking
  ↓
Consensus
  ↓
Conflict Analysis
  ↓
Reasoning          (optional; structured first)
  ↓
Natural Language   (optional; last)
  ↓
UI
```

### Hard rules

1. **No PDF parsing or raw-embedding answers as the product path** for research claims. Inputs enter via Library → Phase 1 → Evidence Layer; intelligence reads EvidenceObjects (and derived aggregates), not “stuff the PDF in the prompt.”
2. **Natural language is the last step**, never the first source of truth.
3. **Consensus and Conflict are aggregation / coded metadata**, not LLM essays. LLMs may narrate coded results only after those stages produce structured output.
4. **Insufficient evidence is a first-class outcome.** Skipping retrieval to “just generate” requires an ADR that explicitly waives this ADD.
5. **One retrieval/ranking substrate.** New features call shared Research Intelligence APIs; they do not invent private search/rank stacks that bypass Evidence Layer semantics.

This extends Constitution Principle 11: consume the Evidence Layer **through** this pipeline, not via ad-hoc model calls.

### Research Intelligence — explicit permissions (Phase 2.3)

**May:**

- Retrieve evidence  
- Rank evidence  
- Aggregate evidence  
- Detect consensus  
- Detect conflicts  
- Explain reasoning (from coded/stored steps)

**May not:**

- Read PDFs directly as the product answer path  
- Bypass the Evidence Layer  
- Invent EvidenceObjects  
- Mutate accepted evidence in place  
- Introduce parallel storage for research knowledge  

**Never owns knowledge (ADR-0006):** RI only computes over Evidence Layer
objects — retrieve / rank / aggregate / link / explain EvidenceObjects.
No second corpus representation.

**One pipeline, not modules (ADR-0006):** stages are Retrieval → Ranking →
Consensus → Conflict → Reasoning → Presentation — each with one API, one
test suite, one contract — not five independent engines.

**Evidence Query first:** Before Retrieval code, freeze the shared Evidence
Query contract (intent, scope, filters, ranking_strategy, result_limit).
Canonical: `docs/architecture/phase-2.3-research-intelligence-pipeline.md`.

Frozen Evidence Layer contracts (EvidenceObject, Explain, bindings, reviews,
provenance, confidence bands) are governed by ADR-0005 — RI adds pipeline
stages; it does not casually reshape the substrate.

---

## 3) Product phase: Phase 2.3 — Research Intelligence

After Evidence Layer **RC** (not before Stage 4 / RC), the next architectural phase is:

> **Phase 2.3 — Research Intelligence**

Not AI chat. Not Week 3. A capability phase on the Evidence Layer substrate (ADD-0005 / ADR-0006).

**No further architecture work is required before `v0.2.0-rc1`.** After RC:
close 2.2 → open 2.3 at Evidence Query freeze → Retrieval.

Provisional “Month N” labels below map 1:1 to **Phase 2.3 sprints**. Do not start until `v0.2.0-rc1` (or equivalent) is tagged.

### Sprint 0 — Evidence Query contract

Freeze the universal ask shape (intent, scope, filters, ranking_strategy, result_limit). All capabilities submit Evidence Queries.

### Sprint 1 — Evidence Retrieval

Today: Sentence → Binding → Evidence.  
Next: Evidence Query → Retrieval stage → EvidenceObjects.

```text
POST /api/evidence/search
POST /api/evidence/retrieve
```

(These are the Retrieval stage API — not a separate product.)

### Sprint 2 — Evidence Ranking

```text
Evidence → Quality → Study Design → Recency → Ranking
```

(Ranking stage reorders EvidenceObjects from Retrieval.)

### Sprint 3 — Consensus

```text
Supporting → Contradicting → Neutral → Consensus
```

No LLM — pure aggregation.

### Sprint 4 — Conflict Analysis

Structured reasons only (population / dosage / method / outcome). No LLM.

### Sprint 5 — Reasoning Pipeline

Still no generation:

```text
Retrieve → Rank → Aggregate → Reason
```

### Sprint 6 — Writing Intelligence

Only then generation consumes the mature pipeline (roadmap Phase 2.4 done correctly).

---

## 3b) Legacy month labels (same sequence)

### Month 2 — Evidence Retrieval (= Sprint 1)

Today: Sentence → Binding → Evidence.  
Next: Question → Evidence Search → Rank → Return.

```text
POST /api/evidence/search
POST /api/evidence/retrieve
```

Every future feature uses the same retrieval layer.

### Month 3 — Evidence Ranking

Not all evidence is equal. Pipeline factors (versioned method):

```text
Study Quality → Recency → Study Type → Acceptance → Contradictions → Final Rank
```

Strongest evidence first; ordinal bands and acceptance status remain visible.

### Month 4 — Consensus Engine

Not “5 papers.” Structured aggregate, **no LLM**:

```text
Consensus: Strong
  supporting: 8
  contradicting: 2
  neutral: 1
```

### Month 5 — Conflict Engine

Not “papers disagree.” Coded mediators from structured metadata:

```text
Conflict
  Population differs | Dosage differs | Method differs | Outcome differs
```

LLM explains only after mediators are coded.

### Month 6 — Evidence Graph (expand, don’t rebuild)

Extend Phase 1.7 KG + EvidenceObject links:

```text
Claim → EvidenceObject → Method → Outcome → Statistic → Limitation
```

No Neo4j mandate; relational + existing KG JSON first (constitution / Week 2 non-goals).

### Month 7 — Writing Intelligence

```text
Retrieval → Ranking → Consensus → Reasoning → Paragraph
```

Generation is the **final** step (unlocks roadmap Phase 2.4 safely).

### Month 8 — Reviewer (compiler-shaped)

```text
Sentence → Evidence Search → Coverage → Citation Check → Support Check → Warnings
```

Not “call GPT on the draft.”

### Month 9 — Research Assistant

```text
Question → Search → Consensus → Conflict → Reasoning → Answer
```

No PDF parsing; no embeddings as the answer path — everything through Evidence Layer + this pipeline.

### Month 10 — Compare

Papers / methods / findings / limitations / evidence strength on a consistent EvidenceObject representation.

### Month 11 — Publication Engine

Journal rules, reporting guidelines, submission readiness, evidence completeness.

### Month 12 — Research Operating System

One foundation:

```text
                 Library
                    │
                    ▼
          Document Understanding
                    │
                    ▼
═══════════════════════════════
        Evidence Layer
═══════════════════════════════
 Objects · Reviews · Bindings
 Provenance · Explain
 Search · Ranking · Consensus · Conflict
═══════════════════════════════
        │
 ┌──────┼─────────┬──────────┐
 ▼      ▼         ▼          ▼
Writing Reviewer Compare Assistant
```

---

## 4) Relationship to Week 2 and Phase 2 roadmap

| Roadmap item | Relationship |
|--------------|--------------|
| Phase 2.2 Evidence Layer MVP | **Platform prerequisite** — must ship before Research Intelligence capabilities |
| Phase 2.3 Citations | Connect library citations; still must not invent evidence |
| Phase 2.4 Guided generation | **Month 7 Writing Intelligence** — blocked until retrieval/rank/consensus exist at MVP quality |
| Phase 2.5 Reviewer | **Month 8** — compiler pipeline, not GPT-first |

Week 2 hard bans remain: no guided generation, no Reasoning chat, no Research Memory, no six engines **in Week 2**.

---

## 5) What this ADD is not

- Not a license to build Months 2–12 before Evidence Layer MVP verification.
- Not a mandate for microservices (“engines”) on day one — shared `backend/evidence/` (and later `intelligence` seams) may grow modules as contracts stabilize.
- Not a replacement for Phase 1.5 / 1.7 — those feed the Evidence Layer; Research Intelligence consumes the layer.

---

## 6) Compliance for new features

A PR that adds research-facing “AI” must answer in the description:

1. Which pipeline stages does it call?
2. Which Evidence Layer APIs does it use?
3. What is the insufficient-evidence UX?
4. Where does NL generation sit (must be last, or N/A)?

If any answer is “we prompt the model with PDF text / chat only,” the PR violates ADD-0005 / Principle 11 unless accompanied by a waiving ADR.
