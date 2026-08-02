# Research Memory

**Document:** `07-RESEARCH-MEMORY.md`  
**Date:** 2026-08-02  
**Pillar:** Memory (lifecycle) — Dhund’s largest future differentiator  
**Timing:** Foundations during P3–P4; flagship product **after** P0–P1 and alongside/after P5 Graph.

**Related:** [05-RESEARCH-OS-VISION.md](05-RESEARCH-OS-VISION.md) · [06-KNOWLEDGE-GRAPH-PRODUCT.md](06-KNOWLEDGE-GRAPH-PRODUCT.md) · `backend/ai/memory_engine.py` · project memory APIs · ADR-0013 (Session — related but distinct)

---

## 1. Thesis

> **Nothing important a researcher does in Dhund should be forgotten.**

Today most AI products are:

```text
Chat → Answer → (maybe) scrollback
```

Dhund’s differentiator:

```text
Paper → Evidence → Memory → Project Context → Long-term Memory → Grounded AI
```

Memory is not “chat history.” It is the **durable research autobiography** of the user: papers, conversations, citations, drafts, hypotheses, reviews, and project decisions — retrievable, inspectable, and usable by Writing and Agents.

---

## 2. What must be remembered

| Class | Examples | Today |
|-------|----------|-------|
| Papers / files | Imports, stubs, syncs | ✅ Library |
| Evidence | EvidenceObjects, accept/reject | ✅ Evidence Layer |
| Conversations | Chat threads, paper chat | 🟡 Stored; weak ranking |
| Citations | Manager entries, WI bindings | 🟡 Manager; insert gap |
| Drafts / versions | Writing documents | ✅ Shell |
| Hypotheses | Research questions, framing | 🟡 Project questions; Framing incomplete |
| Reviews | Reviewer runs / findings | ✅ BE; FE thin |
| Project prefs | Goals, memory blobs | 🟡 Project memory APIs |
| Decisions | Accept/reject, export gates | 🟡 Decisions + workflow events |
| Integration events | Syncs, Drive arrivals | 🟡 Sync runs; incomplete |

**Target:** One Memory substrate that can answer: *“What have I already decided or learned about X?”* with citations to artifacts.

---

## 3. Memory layers

```text
Ephemeral working set     ← current Writing / chat turn
    ↑
Project Memory            ← goals, open questions, pinned claims
    ↑
Long-term Research Memory ← cross-project corpus of episodes + embeddings
    ↑
Knowledge Graph           ← structured projection (see 06)
```

| Layer | Job | Store |
|-------|-----|-------|
| Working set | Prompt context for this task | Existing Prompt/WI context builders |
| Project Memory | Sticky project truth | Extend `backend/projects/memory.py` |
| Long-term Memory | Cross-session recall | New memory episodes + embeddings (ADR) |
| Knowledge Graph | Structured navigation | Derived from Evidence + Memory |

**Chat becomes a writer into Memory**, not the home of truth.

---

## 4. Current engineering gaps

| Gap | Detail |
|-----|--------|
| `memory_engine.py` | Token-overlap TODO; no real embeddings rank |
| Dual AI paths | Chat may not write structured memory episodes |
| No unified Memory API | Scattered notes / project memory / workflow events |
| ADR-0013 Research Session | Deferred hub — complementary; do not confuse with LT Memory |
| No hypothesis object | Framing cards not shipped |
| Forgotten reviews | Reviewer runs not first-class in “what I learned” |

---

## 5. Product roadmap (**P6 Memory**)

### P6.a — Memory episodes (foundation)

Define a durable episode:

```text
MemoryEpisode {
  id, user_id, project_id?,
  kind: paper|evidence|chat|citation|draft|hypothesis|review|decision|sync,
  ref_type + ref_id,   // points at existing rows — no duplicate blobs
  summary,             // short, human + machine
  created_at, embedding?
}
```

| Work | Effort |
|------|--------|
| Schema + write hooks from existing events | L |
| `GET /api/memory/search` (project + global) | M |
| Settings: what to remember / forget | M |

**Rule:** Episodes **reference** Evidence/files/docs — they do not fork content.

### P6.b — Retrieval for Grounded AI

| Work | Effort |
|------|--------|
| Replace token-overlap with embedding retrieval | L |
| WI + Evidence Assistant consume Memory + Evidence | L |
| “Remember this” / “Forget this” UX | M |

### P6.c — Hypotheses & framing

| Work | Effort |
|------|--------|
| Hypothesis / framing cards → episodes | L |
| Link hypotheses ↔ evidence ↔ drafts | L |

### P6.d — Continuous Research

| Work | Effort |
|------|--------|
| Monitoring events → Memory (“new paper on watched topic”) | L |
| Agents read/write Memory (see 08) | XL |

---

## 6. UX principles

1. **Nothing important forgotten** — default remember; explicit forget.  
2. **Inspectable** — open the source artifact from any memory hit.  
3. **Project-first, global optional** — avoid noisy cross-project bleed.  
4. **Writing asks Memory first** — “Have I written about this?” / “What evidence did I accept?”  
5. **Privacy** — export/delete memory with account (Enterprise: retention policies).

---

## 7. Relationship to Knowledge Graph

| Memory | Graph |
|--------|-------|
| Episodic (“I accepted claim C on date D”) | Structural (“C conflicts with C2”) |
| Good for recall & chronology | Good for navigation & synthesis |
| Feeds graph rebuilds | Projects memory into explorable form |

Both are required. Graph without Memory is a pretty map with amnesia. Memory without Graph is a dump.

---

## 8. Success metrics

| Metric | Meaning |
|--------|---------|
| Repeat-question deflection | System surfaces prior answers/evidence |
| % WI runs using Memory hits | Memory is in the loop |
| Time to resume a cold project | Minutes, not re-upload/re-chat |
| User trust: “Dhund remembers my research” | Qualitative Alpha/Beta |

---

## 9. Non-goals

- Training foundation models on user memory without consent  
- Silent cross-user memory  
- Replacing EvidenceObjects with freeform “memories” as truth  
- Building ADR-0013 Session Engine as a substitute for LT Memory (different problem)

---

## 10. Sequencing

```text
P0–P1  Trust + Library (Memory write quality improves as evidence/writing stabilize)
P3     Feature flags + quotas (gate Memory retrieval cost)
P5     Graph product (structured view)
P6     Research Memory flagship  ← this doc
P7     Agents read/write Memory continuously
```
