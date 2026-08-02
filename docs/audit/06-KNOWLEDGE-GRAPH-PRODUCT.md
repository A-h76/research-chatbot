# Knowledge Graph as a First-Class Product

**Document:** `06-KNOWLEDGE-GRAPH-PRODUCT.md`  
**Date:** 2026-08-02  
**Pillar:** Knowledge (lifecycle step)  
**Timing:** **After P4** engineering roadmap for flagship productization; polish existing graphs during P0–P3 without rewriting freezes.

**Related:** [05-RESEARCH-OS-VISION.md](05-RESEARCH-OS-VISION.md) · [07-RESEARCH-MEMORY.md](07-RESEARCH-MEMORY.md) · RI-005 project graph · paper Phase 1.7 KG

---

## 1. Why this is flagship (not an internal component)

Today the Knowledge Graph is treated as an analysis artifact:

- Per-paper Phase 1.7 graph JSON  
- Project RI-005 graph from EvidenceObjects (`backend/evidence/graph.py`)  
- UI panels on Analysis / Evidence surfaces  

That is **infrastructure**. The Research OS vision requires the graph to become the **persistent, explorable memory of everything the researcher has learned** — the product researchers open *before* they write.

```text
Today:     Import → Evidence → Writing
Flagship:  Import → Evidence → Knowledge Graph → Research Memory → Writing → Publishing
```

---

## 2. Product job-to-be-done

> “Show me what I know about X — across every paper, claim, method, author, and contradiction I’ve ever touched — so I can write and discover from knowledge, not from a file list.”

---

## 3. Current state (honest)

| Layer | Status | ~% | Notes |
|-------|--------|---:|-------|
| Paper KG (1.7) | MVP | 70 | In-process; Paper Graph tab |
| Project RI graph | MVP | 80 | From EvidenceObjects; Analysis/Evidence UI |
| KG v2 / Neo4j | Deferred | 0 | Track 2; usage-gated |
| Concept / author / citation graphs as product | Not started | 5 | Design only |
| Contradiction / novelty graphs | Partial APIs | 40 | Conflict/consensus APIs exist; not graph product |
| Graph → Writing deep link | Partial | 35 | WI uses evidence; not “compose from graph selection” |
| Graph as home surface | Absent | 0 | Library/Projects are home |

---

## 4. Graph families (future product surface)

Build as **read models over Evidence + Library + Citations**, not a second truth store.

| Graph | Nodes | Edges | Researcher value |
|-------|-------|-------|------------------|
| **Concept graph** | Terms, themes, constructs | co-occurs, subsumes, related | Topic landscape |
| **Author graph** | Authors | co-author, cites | Who shapes the field |
| **Institution graph** | Labs / universities | affiliation | Collaboration map |
| **Citation graph** | Papers / works | cites, cited-by | Lineage |
| **Methodology graph** | Methods, designs, measures | used-in, compares-to | Method shopping |
| **Contradiction graph** | Claims / EvidenceObjects | conflicts, mediates | Scientific tension |
| **Novelty graph** | Claims / gaps | novel-vs, fills-gap | What’s new |

**Constraint:** Edges must point back to EvidenceObject IDs and/or library file IDs for Inspect.

---

## 5. Product roadmap (post-P4 — call it **P5 Graph**)

### P5.a — Unify the two graphs (foundation)

| Work | Outcome |
|------|---------|
| Single “Knowledge” product entry (project-scoped) | One home for graph exploration |
| Paper KG + RI graph as layers/filters | Stop dual UX confusion |
| Deep link node → Evidence Inspector → Writing | Graph becomes spine, not sidebar |
| Persist derived graph snapshots (versioned) | Not only live compute |

Effort: **L** · Depends on: Evidence freeze (done), extract quality

### P5.b — Concept + contradiction graphs (differentiator)

| Work | Outcome |
|------|---------|
| Concept nodes from themes/matrix/extract | Concept graph v1 |
| Contradiction edges from conflict engine | Contradiction graph v1 |
| “Explain this edge” → EvidenceObjects | Trust |

Effort: **L**

### P5.c — Citation + author + methodology graphs

| Work | Outcome |
|------|---------|
| Citation graph from Crossref/S2/library metadata | Lineage view |
| Author / institution projections | People/org map |
| Methodology graph from RI methodology stage | Method compare |

Effort: **L–XL**

### P5.d — Novelty graph + writing from selection

| Work | Outcome |
|------|---------|
| Novelty / gap nodes tied to RI gaps | Research planning |
| Multi-select nodes → Writing Intelligence scope | Compose from knowledge |
| Optional Neo4j / graph DB **only with ADR + demand** | Scale projection |

Effort: **XL**

---

## 6. UX principles

1. **Inspectability** — every edge opens evidence.  
2. **Project-scoped by default** — personal OS first; org graphs later (Enterprise).  
3. **Writing is a consumer** — select subgraph → grounded draft.  
4. **No orphan graph** — if Evidence is deleted/rejected, edges retire.  
5. **Progressive complexity** — start with concept + contradiction; don’t ship seven empty tabs.

---

## 7. Engineering principles

- Extend `backend/evidence/graph.py` + paper KG serializers; do not invent a parallel store without ADR.  
- Derived tables / materialized views OK if they reference evidence/file IDs.  
- Worker jobs for heavy graph rebuild (`theme_map`-style HANDLER).  
- Feature-flag each graph family.  
- Align with Research Memory ([07](07-RESEARCH-MEMORY.md)) — Memory stores episodes; Graph stores structure.

---

## 8. Success metrics

| Metric | Target |
|--------|--------|
| Graph opens/week per active researcher | Rising vs Writing-only sessions |
| % of grounded drafts scoped from graph selection | >30% of WI runs (mature) |
| Edge → Inspector open rate | High (trust loop) |
| Time-to-“what do I know about X” | Minutes, not re-reading PDFs |

---

## 9. Explicit non-goals (until P5)

- Replacing EvidenceObjects with freeform graph nodes  
- Neo4j as default in P0–P3  
- Public knowledge graph sharing before teams AuthZ  
- Marketing “AI Knowledge Graph” without Inspect  

---

## 10. Sequencing vs engineering roadmap

```text
P0–P1  Finish Evidence → Writing trust + Library
P2–P3  More sources + hardening (graph polish OK)
P4     SaaS / collab hooks
P5     Knowledge Graph as flagship product  ← this doc
P6+    Memory depth + Agents consume the graph
```
