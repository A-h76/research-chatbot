# Dhund Product Constitution v1

**Status:** **Frozen** — binding for product and UI decisions after this date.  
**Date:** 2026-08-08  
**Type:** Product / experience governance (not an engineering rewrite plan)  
**Companions:** [`00-constitution.md`](00-constitution.md) · [`ENGINEERING-CONSTITUTION-v1.md`](ENGINEERING-CONSTITUTION-v1.md) · [`DHUND-DESIGN-LANGUAGE-v1.md`](DHUND-DESIGN-LANGUAGE-v1.md) · [`adr/0018-assistant-engine-research-state.md`](adr/0018-assistant-engine-research-state.md)

**Intent:** Keep Dhund from becoming either a generic AI chatbot or Jira-for-research.  
Backend may be deep. The interface must stay task-simple.

**Hard rule after freeze:** Prefer improving a researcher screen over opening a new engine, slice, or orchestration layer. Resume deferred backend layers only when the UI says *“I wish the backend knew this.”*

---

## The seven principles

### 1. Researcher First

> **Design every interaction from the researcher's mental model. Engineer every system from the engineer's mental model.**

UI speaks workflow and outcomes. Code speaks cores, contracts, and evidence. Never invert those.

---

### 2. Think Before Speaking

> **Dhund decides before it generates. Every response should be grounded in intent, context, and research state before reaching an LLM.**

Assistant Engine → (optional) Capability Router → Prompt Builder → LLM.  
Greetings and pure workflow direction may stay local. No capability dumps.

---

### 3. Evidence Before Intelligence

> **Every insight, recommendation, and generated output should be grounded in traceable evidence whenever possible.**

Aligns with Master Constitution §11 (Evidence First). LLMs explain and organize; they do not invent the research record.

---

### 4. Invisible Intelligence ⭐

> **The system may know everything. The interface should reveal only what helps the researcher accomplish the current task.**

The backend can know stage, journey, confidence, blockers, themes, gaps, evidence, contradictions, writing progress.

The UI should show only:

- **one status**
- **one recommendation**
- **one piece of context**

Research State is **internal**. Product UI consumes thin view hints (`title` / `subtitle` / `primaryAction`), not a Research State dump.

---

### 5. Workflow Over Features

> **Researchers come to complete research, not use tools. Navigation should represent the research workflow, not Dhund's internal capabilities.**

**Good:** Library · Research Intelligence · Writing · Review  

**Bad (as top-level nav):** Evidence · Graph · Matrix · Timeline · Entities  

Internal lenses may live *inside* Research Intelligence; they are not primary destinations.

---

### 6. Progressive Disclosure

> **Reveal complexity only when the researcher needs it. Never overwhelm a beginner to satisfy an expert.**

Home: “Continue your literature review.”  

Not: Coverage 82% · Stage Writing · Evidence 642 · Themes 12 · Contradictions 4.

Experts get density *inside* the task (RI, Reviewer), not a KPI wall on Home.

---

### 7. One Purpose Per Screen

Every screen answers exactly one primary question — and owns one emotional outcome.

| Screen | Question | Emotional outcome |
|--------|----------|-------------------|
| Home | What should I do next? | Orientation (calm, invisible) |
| Projects | Which research should I continue? | Continuity |
| Library | Which papers matter? | Effortless control |
| Paper | What does this paper say? | Understanding |
| Research Intelligence | What does the corpus say? | Insight (signature / “magical”) |
| Writing | How do I write from evidence? | Flow |
| Review | What should I improve before publishing? | Confidence |

If a screen answers multiple unrelated questions, split the responsibility.

---

### 8. Home Invisible · Intelligence Magical ⭐

> **Home should feel invisible. Research Intelligence should feel magical.**

Home’s job is **orientation** — restore context and create one next milestone. It must not carry brand spectacle, signature visualizations, or feature theater.

Dhund’s signature lives where researchers *work*:

- Evidence Inspector
- Provenance visualization
- Research Intelligence
- Evidence-backed Writing
- Review workflow

**Freeze (2026-08-08):** Home is **frozen** for craftsmanship polish. Touch Home only for real usability bugs or Research State contradictions — not for another week of visual refinement. Next Phase 2 investment order: **Projects → Library → Research Intelligence → Writing → Review**.

---

## Design filter (use on every feature proposal)

1. **Does this help the researcher complete their current task?**
2. **Can this be inferred instead of shown?**
3. **Does it belong on this screen?**
4. **Is this exposing engineering instead of research?**
5. **If removed, would the researcher actually miss it?**

If #5 is **no**, it should not be visible by default.

---

## Design review opener

Every design / product review starts with:

> **Which researcher task are we improving today?**

Not:

> Which system are we building today?

---

## Success criterion

When someone opens Dhund, they should not think:

> “This is a sophisticated AI system.”

They should think:

> **“This is exactly how research should have worked all along.”**

---

## Relationship to engineering freeze

| Frozen platform cores | Product phase |
|----------------------|---------------|
| Assistant Engine · Research State · Capability Router · Workflow Engine | Phase 2 = frontend UX: **Home ✓ frozen** → **Projects (in progress)** → Library → Paper → RI → Writing → Review → mobile → polish |

Deferred until friction demands: Journey Engine, Skill Registry, Research Memory, Mentor Analytics (see ADR-0018).

**Craftsmanship note:** Prefer craftsmanship (presence, motion, companion feel) over feature accretion once a screen answers its one question. Do not reopen a frozen surface for 1% polish while a higher-impact surface is unsolved.
