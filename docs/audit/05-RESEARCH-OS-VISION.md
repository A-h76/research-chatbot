# Research OS Vision (North Star)

**Product:** Dhund  
**Document:** `05-RESEARCH-OS-VISION.md`  
**Date:** 2026-08-02  
**Audience:** Founders, product, engineering — every future feature must strengthen one step below.

**Related:** [04-RESEARCH-OS-ROADMAP.md](04-RESEARCH-OS-ROADMAP.md) · [06-KNOWLEDGE-GRAPH-PRODUCT.md](06-KNOWLEDGE-GRAPH-PRODUCT.md) · [07-RESEARCH-MEMORY.md](07-RESEARCH-MEMORY.md) · [08-RESEARCH-AGENT-LAYER.md](08-RESEARCH-AGENT-LAYER.md) · [09-ENTERPRISE-ROADMAP.md](09-ENTERPRISE-ROADMAP.md) · [10-RESEARCH-ECOSYSTEM-MASTERPLAN.md](10-RESEARCH-ECOSYSTEM-MASTERPLAN.md)

---

## 1. One question

> **When Dhund is finished, what does it actually do?**

Not architecture. Not backend. Not UI chrome.

Dhund is the **Research Operating System**: a durable environment where a researcher’s questions, papers, evidence, memory, writing, and continuous monitoring live in one grounded loop — nothing important is forgotten, nothing important is invented without evidence.

---

## 2. The research lifecycle (North Star)

```text
Researcher
    ↓
Question
    ↓
Discovery          ← find what exists (library, PubMed, Drive, peers…)
    ↓
Evidence           ← extract claims that can be inspected and trusted
    ↓
Memory             ← persist what was learned (papers, chats, drafts, hypotheses)
    ↓
Knowledge          ← structure memory as a first-class Knowledge Graph
    ↓
Writing            ← compose grounded manuscripts from evidence + knowledge
    ↓
Review             ← critique unsupported / weak / conflicting claims
    ↓
Publishing         ← export with provenance (MD → DOCX/journal packs)
    ↓
Monitoring         ← watch topics, libraries, folders for change
    ↓
Continuous Research ← loop back to Question with fuller memory
```

**Every future feature must strengthen at least one step.**  
If it does not map to a step, it is not Research OS work — it is distraction.

---

## 3. What Dhund is / is not

| Dhund **is** | Dhund **is not** |
|--------------|------------------|
| An OS for private research work | A ChatGPT skin with PDF upload |
| Evidence-first and inspectable | A black-box summarizer |
| Persistent research memory | A disposable chat thread |
| A graph of what the researcher knows | A folder of PDFs |
| Grounded writing → review → publish | Autocomplete for papers |
| An ecosystem of research sources | A logo wall of “integrations” |
| Continuously monitoring research | One-shot import and forget |

---

## 4. Evolution of the product spine

### Today (honest)

```text
Import → Evidence → Writing → (partial cite/export)
```

Chat exists as a **tool**, not the spine. Knowledge Graph and Memory exist as **partial internals**, not flagship products. Agents and Publishing packs are thin or absent.

### Near-term (finish the OS core — P0–P1)

```text
Import → Evidence → Writing → Review → Cite → Export
         + durable Library
```

### Mid-term (flagship differentiators — after P4 eng roadmap)

```text
Import → Evidence → Knowledge Graph → Research Memory
       → Writing → Review → Publishing → Monitoring
```

### Long-term (enduring Research OS)

```text
Goal → Agents (plan/search/read/evidence/write/review/publish)
     → Memory + Graph always updated
     → Continuous Research
```

See [08-RESEARCH-AGENT-LAYER.md](08-RESEARCH-AGENT-LAYER.md). Not V1.

---

## 5. Five strategic pillars (post-engineering roadmap)

These sit **above** the P0–P4 engineering roadmap. P0–P4 make the OS real; pillars make it enduring.

| Pillar | Document | Role in lifecycle |
|--------|----------|-------------------|
| Knowledge Graph as product | [06](06-KNOWLEDGE-GRAPH-PRODUCT.md) | Knowledge |
| Research Memory | [07](07-RESEARCH-MEMORY.md) | Memory → Continuous Research |
| Research Agent Layer | [08](08-RESEARCH-AGENT-LAYER.md) | Automation of the whole loop |
| Enterprise readiness | [09](09-ENTERPRISE-ROADMAP.md) | Trust for labs / universities |
| Research Ecosystem | [10](10-RESEARCH-ECOSYSTEM-MASTERPLAN.md) | Discovery + Monitoring inflows |

---

## 6. Design constraints (non-negotiable)

1. **Evidence remains the unit of trust.** Graphs and memory store and organize EvidenceObjects (and derived edges) — they do not replace them.  
2. **No parallel knowledge store** without ADR (constitution / IDD-0010).  
3. **Finish P0–P1 before pillar builds.** Flagship KG/Memory must not derail lit-review trust or library durability.  
4. **Integrations must change the product**, not only add OAuth badges — see Ecosystem Masterplan.  
5. **Chat answers without citations are demoted.** Long-term Research Assistant must cite EvidenceObject IDs.  
6. **Enterprise does not rewrite the personal OS** — it wraps it (RBAC, audit, residency).

---

## 7. Definition of “finished”

Dhund is finished for a researcher when:

1. They can ask a question and discover relevant work across library + connected sources.  
2. Claims become inspectable Evidence.  
3. Everything learned is remembered (papers, chats, citations, drafts, hypotheses, reviews).  
4. Knowledge is explorable as a graph (concepts, authors, methods, contradictions, novelty).  
5. Writing, review, and publishing consume that memory/graph with provenance.  
6. The system can monitor the world and continue research without starting from zero.  
7. Labs can adopt it with enterprise controls when they outgrow personal beta.

Until then, we ship increments that **move the lifecycle forward** — not feature checklists for their own sake.

---

## 8. How to use this document

- **Product:** Map every epic to a lifecycle step.  
- **Engineering:** P0–P4 in [04](04-RESEARCH-OS-ROADMAP.md) first; then pillar roadmaps.  
- **Marketing:** Only claim Live steps that the audit scoreboard marks Production/MVP with honest gaps.  
- **Hiring / investors:** This is the Research OS thesis; P0–P4 is the near-term execution plan.
