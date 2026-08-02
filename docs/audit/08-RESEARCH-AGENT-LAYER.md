# Research Agent Layer

**Document:** `08-RESEARCH-AGENT-LAYER.md`  
**Date:** 2026-08-02  
**Pillar:** Continuous Research / Automation (lifecycle)  
**Timing:** **Not V1.** After P0–P1 trust, P5 Graph foundations, and P6 Memory episodes. Call this **P7 Agents**.

**Related:** [05-RESEARCH-OS-VISION.md](05-RESEARCH-OS-VISION.md) · [07-RESEARCH-MEMORY.md](07-RESEARCH-MEMORY.md) · `worker.py` HANDLERS · `backend/workflow/`

---

## 1. Why agents (and why not yet)

Today “automation” is mostly:

```text
Watch topic / sync library → Import job
```

That is **pipeline automation**, not **research agency**.

The Research OS endgame:

```text
Research Goal
    ↓
Planner Agent
    ↓
Search Agent → Reading Agent → Evidence Agent
    ↓
Writing Agent → Reviewer Agent → Publication Agent
    ↓
Memory + Knowledge Graph updated
    ↓
Monitoring Agent → loop
```

Agents **orchestrate** existing Evidence, Writing Intelligence, Reviewer, Library, and Memory — they do not invent a second research stack.

---

## 2. Principles

1. **Tools over magic** — each agent calls frozen APIs / HANDLERS (EvidenceQuery, extract, WI, sync).  
2. **Human gates** — accept evidence, export, publish remain human-confirmable (especially Reviewer severity=error).  
3. **Memory-native** — every agent writes Memory episodes.  
4. **Budget-bound** — quotas + feature flags + kill switch.  
5. **No Celery rewrite** — agent steps are `job_type`s or a single `research_agent_run` orchestrator using existing SKIP LOCKED.  
6. **Not for V1 / Private Alpha** — finish unassisted *manual* lit-review first.

---

## 3. Agent roster (future)

| Agent | Job | Consumes | Produces |
|-------|-----|----------|----------|
| **Planner** | Decompose research goal into tasks | Goal, Memory, Graph | Plan (steps, scopes) |
| **Search** | Find works across library + scholarly + Drive | Plan queries | Candidate works / stubs |
| **Reading** | Prioritize and “read” (extract + phase1) | Files / PDFs | Analysis + extract jobs |
| **Evidence** | Run extract/review loops; propose accepts | Chunks | EvidenceObjects + review queue |
| **Writing** | Invoke Writing Intelligence with scope | Accepted evidence + Memory | Draft + bindings |
| **Reviewer** | Run Research Reviewer; block bad exports | Draft | Findings + gate |
| **Publication** | Pack export (MD → later DOCX/journal) | Approved draft | Artifacts + trail |
| **Monitoring** | Topic/folder/library watches | Ecosystem connectors | New imports + Memory |

Optional later: **Compare Agent**, **Novelty Agent** (Track 2).

---

## 4. Contrast with today’s worker

| Today HANDLERS | Agent layer |
|----------------|-------------|
| `import`, `phase1_analysis`, `evidence_extract`, … | Composes those jobs |
| User clicks Extract / Generate | Goal → plan → multi-step run |
| Workflow events (telemetry) | Same events + agent run log |
| Sync / watch (thin) | Monitoring Agent owns watches |

**Do not** replace HANDLERS — **register** `agent_plan`, `agent_step`, or reuse existing types under an orchestrator row (`research_runs`).

---

## 5. Product roadmap (**P7**)

### P7.a — Research Run skeleton

| Work | Effort |
|------|--------|
| `research_runs` + steps table (status, budget, project_id) | M |
| UI: Goal → Plan preview → Approve → Run | L |
| Kill / pause run | M |

### P7.b — Search + Reading + Evidence agents

| Work | Effort |
|------|--------|
| Search agent over library + PubMed/OpenAlex | L |
| Auto-enqueue import/phase1/extract with caps | L |
| Human accept queue (no silent accept) | M |

### P7.c — Writing + Reviewer + Publication agents

| Work | Effort |
|------|--------|
| WI invocation from approved evidence set | M |
| Reviewer gate before publish step | M |
| Export artifact + Memory episode | M |

### P7.d — Monitoring agent

| Work | Effort |
|------|--------|
| Topic watch + Drive folder watch → run steps | L |
| Notify (email → later in-app) | M |

---

## 6. UX

```text
“Review literature on GLP-1 and cardiovascular outcomes (2019–2026)”
        ↓
Plan (editable)
  1. Search PubMed + library
  2. Import top 20
  3. Extract evidence
  4. You accept claims
  5. Draft lit-review
  6. Reviewer
  7. Export
        ↓
Run with progress + Memory trail
```

Researchers stay **principal**; agents are **staff**.

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Cost blowups | Hard step budgets; quotas; kill switch |
| Silent wrong science | No auto-accept evidence; Reviewer gate |
| Parallel “agent brain” store | Forbidden — use Evidence + Memory |
| Scope creep before Alpha | Keep this doc aspirational until P6 |

---

## 8. Success metrics

| Metric | Target |
|--------|--------|
| Runs completed with human accepts | Quality > quantity |
| Cost per successful lit-review run | Tracked in ledger |
| % of draft claims bound to evidence | Same as manual WI bar |
| Researcher trust | Prefer agent assist over raw chat |

---

## 9. Sequencing

```text
P0–P1  Manual trust vertical (required)
P2     Ecosystem sources (Search agent fuel)
P5–P6  Graph + Memory (agent context)
P7     Research Agent Layer  ← this doc
```
