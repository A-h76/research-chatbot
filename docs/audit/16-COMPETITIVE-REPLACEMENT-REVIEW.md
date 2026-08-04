# 16 — Competitive Replacement Review

**Document:** `16-COMPETITIVE-REPLACEMENT-REVIEW.md`  
**Role:** Internal product review gate (not a roadmap)  
**Status:** ✅ **Template complete** — Phase 2B (#22–28) 🟢; **fill next** with real researchers — do **not** treat blank rows as product claims  
**Created:** 2026-08-03  
**Updated:** 2026-08-04 (Research Progress KPI · Cognitive Load Audit · primary-workspace honesty · Product Doctrine v2)  
**Trigger:** After #28 OneDrive is Production Ready ([12](12-PHASE2-COMPLETION-TRACKER.md)) — **now live**

**How this document changes decisions**

Earlier process:

```text
Roadmap → Build → Next roadmap item
```

This review enforces:

```text
Build
     ↓
Real researchers use it
     ↓
Where did they leave Dhund?
     ↓
Fix that
     ↓
Repeat
```

That is how durable research tools evolve — not by feature count.

| Document | Question |
|----------|----------|
| [11](11-VERSION1-COMPLETION-TRACKER.md) V1 Tracker | Did we build it correctly? |
| [12](12-PHASE2-COMPLETION-TRACKER.md) Phase 2 Tracker | Did we complete the engineering? |
| **This review (#16)** | Can researchers actually live inside Dhund as their **primary research workspace** — and advance their research while doing so? |

---

## What this document decides

**Before:** “What’s next on the roadmap?”  
**Now:** “Can Dhund become a researcher’s primary research workspace?”

```text
Phase 2 complete
      ↓
Can researchers actually live inside Dhund?
      ↓
YES → Then build flagship pillars
NO  → Fix daily workflows first
```

This sits between **engineering completion** and **strategic expansion**. Replacing Anara / SciSpace / Jenni is a **consequence** of reducing *unnecessary* context switching — not the objective itself.

> **Primary-workspace claims require real-user validation, not only engineering completion.**

```text
Engineering Complete
      ↓
Internal Team Validation
      ↓
10–20 Researchers Use Dhund
      ↓
This Review (diary + scorecard + session / progress / cognitive KPIs)
      ↓
Marketing / positioning claims
```

“Technically possible” ≠ “researchers actually live here.”

---

## One question

> **Can Dhund become a serious researcher’s primary research workspace today?**

### Healthy definition of “primary workspace”

Do **not** optimize only for “never leave.”

Sometimes leaving is correct:

* Reading a publisher’s HTML version
* Submitting to a journal
* Collaborating in Overleaf when the lab requires it

The goal is **not** “never leave.”

The goal is:

> **Leave only when there is a genuine external requirement — not because Dhund is missing an essential workflow.**

Researchers may still open Google Scholar, a publisher site, or Overleaf for specific tasks. Success means Dhund is where they **spend most of their research day**, and where leaving is deliberate — not forced by gaps.

Answer from **workflows + context switching + research progress + cognitive load + differentiation + real users** — not feature count.

---

## When to fill this

```text
V1 🟢 → Phase 2A (#21) 🟢 → Phase 2B (#22–28) 🟢 → THIS REVIEW → next milestone
```

Do **not** jump to Knowledge Graph / Research Memory / Agents / Enterprise before this review.

This is the shift from **engineering-driven development** (ship acquisition without changing the pipeline) to **researcher-driven product development** (what still forces them to leave — and did their research actually move forward?).

---

## Review questions

* Can a PhD student complete a literature review entirely inside Dhund?
* Can a PhD student realistically spend an entire week inside Dhund?
* Can they stop constantly switching between Anara, SciSpace, Jenni, Zotero, and a PDF reader?
* Is every major **daily** research task possible without leaving the platform for *Dhund gaps* (vs genuine external requirements)?
* Where do they still leave Dhund — and why?
* Is the biggest remaining gap PDF reading, annotation, synthesis, publication, or collaboration?
* Where is Dhund clearly better (not merely at parity)?
* Did **Research Session Completion** improve vs last review?
* Did they **advance their research** (Research Progress KPI) — or only stay logged in?
* Did Dhund **reduce decisions** they had to make (Cognitive Load Audit)?

---

## Critical vs future (do not block launch on pillars)

**Not** every row must be ✅ before shipping or launching.

| Tier | Workflows | Must be strong? |
|------|-----------|-----------------|
| **Critical daily** | Discover · Import · Analyze · Understand · Compare · Write · Review · Export | Yes — enough that users don’t constantly leave *for Dhund gaps* |
| **Future differentiators** | Knowledge Graph Product · Research Memory · Agents · Continuous Monitoring · Enterprise | No — may stay ❌ (e.g. Memory until P6, Graph until P5) without blocking a compelling product |

Flagship pillars amplify a complete daily workflow; they should not compensate for missing day-to-day capability.

---

## Research Session Completion (north-star continuity KPI)

Can one researcher complete this entire workflow without leaving Dhund *for a Dhund gap*?

```text
□ Discover
□ Import
□ Read
□ Highlight
□ Annotate
□ Compare
□ Extract
□ Accept Evidence
□ Write
□ Review
□ Export
□ Return next day
```

**Target:** maximize checked boxes with real users over time.  
Every milestone should move this KPI — or it is not priority over unfinished daily workflows.

This measures **research continuity** (less context switching). Alone it is incomplete — see Research Progress below.

---

## Research Progress KPI (north-star outcome KPI)

Researchers don’t care only whether they stayed inside Dhund.  
They care whether they **actually advanced their research**.

Alongside “Did they stay?” ask: **“Did they move their research forward?”**

| Question | Yes / No | Notes |
|----------|----------|-------|
| Did they identify a relevant paper? | | |
| Did they understand it faster than before Dhund? | | |
| Did they discover something new (claim, gap, conflict, method)? | | |
| Did they answer (or meaningfully advance) their research question? | | |
| Did they produce a publishable or advisor-ready output? | | |

This measures **research velocity and quality**, not software usage.

Generic engagement metrics (DAU, session time, chat count) are secondary.  
If Session Completion is high but Research Progress is low, Dhund is a sticky empty shell — fix outcomes, not only retention.

---

## Cognitive Load Audit

Every major workflow should ask:

> **How many decisions did the researcher have to make?**

Prefer fewer, clearer decisions — and default the rest.

**Today (example — high load):**

```text
Search → Choose provider → Import → Analyze → Extract → Accept → Write
```

**Target (example — lower load):**

```text
Ask question → Dhund suggests papers → User confirms → Everything else happens
```

| Workflow | Decisions required today | Decisions after change | Load ↓? |
|----------|--------------------------|------------------------|---------|
| Discover / import | _TBD_ | _TBD_ | |
| Paper understanding | _TBD_ | _TBD_ | |
| Evidence accept | _TBD_ | _TBD_ | |
| Write / cite | _TBD_ | _TBD_ | |
| Review / export | _TBD_ | _TBD_ | |

Less mental effort → better product.  
If a feature adds AI surface area but *increases* decisions, it fails this audit.

---

## Research Week Diary (fill with a real researcher)

Instead of only scoring workflows, **simulate one researcher** across a week.

Researchers don’t work in isolated features. They work across an entire week. The diary captures that — better than “Please rate PDF Reader.”

```text
Monday (example arc)
Question → Search → Import → Read → Extract → Write notes → Draft → Review → Export
```

Ask: **Where did they leave Dhund?**  
Also note: **Did that leave advance research?** (genuine external need vs Dhund gap)

| Time | Activity | Stayed? | Left for | Why? | Progress? |
|------|----------|---------|----------|------|-----------|
| 9:00 | Search | ✅ / ❌ | | | |
| 9:15 | Read PDF | ✅ / ❌ | e.g. Acrobat | Better annotations? | |
| 10:00 | Take notes | ✅ / ❌ | e.g. Obsidian | Better linking? | |
| 11:00 | Write | ✅ / ❌ | | | |
| 14:00 | References | ✅ / ❌ | e.g. Zotero | Easier editing? | |
| … | … | | | | |

One honest diary often exposes more usability issues than hundreds of feature comparisons. Repeat for Tue–Fri if useful; Monday alone is enough for a first pass.

---

## Context Switching Audit (fill after #28 + user validation)

During a normal research week, **when does a researcher leave Dhund?**

Identifies **workflow gaps**, not feature gaps.

Classify each leave:

* **Forced (Dhund gap)** — missing essential workflow → fix in product  
* **Legitimate (external requirement)** — journal, lab, publisher HTML → OK; don’t over-optimize

| Task | Leaves Dhund? | Destination | Why | Forced / Legitimate |
|------|---------------|-------------|-----|---------------------|
| Discover papers | _TBD_ | e.g. PubMed / Scholar | Missing capability? | |
| Import / organize library | _TBD_ | e.g. Zotero | Missing workflow? | |
| Read PDFs | _TBD_ | e.g. Acrobat / browser | Better annotation? | |
| Take notes | _TBD_ | e.g. Obsidian / Notion | Missing linked notes? | |
| Organize references | _TBD_ | e.g. Zotero | Missing workflow? | |
| Compare / synthesize papers | _TBD_ | e.g. SciSpace / Notion | Missing workspace? | |
| Write manuscript | _TBD_ | e.g. Word / Jenni | Missing editor? | |
| Review / verify claims | _TBD_ | e.g. manual PDF hunt | Missing evidence trail? | |
| Collaborate | _TBD_ | e.g. Google Docs | Missing collaboration? | |
| Publish / revise for journal | _TBD_ | e.g. Overleaf / Word | Missing publication tools? | |

---

## Workflow scorecard (fill after #28)

Score **workflows**, not features.  
Status: ✅ primary-workspace ready · 🟡 partial · ❌ cannot rely on Dhund (OK for future pillars).

Also ask: **Why would someone make Dhund their primary workspace?** (competitive advantage — differentiation, not only parity.)

| Workflow | Ready? | Competitive advantage | Why / Remaining gap |
| -------- | ------ | --------------------- | ------------------- |
| Literature discovery | _TBD_ | _TBD_ | Multi-source acquisition (#22–28) |
| Paper understanding | _TBD_ | e.g. Analysis 2.0 + inspectable quality | SUE + Evidence |
| PDF reading & annotation | _TBD_ | _TBD_ | Reader / annotation depth |
| Evidence-linked notes | _TBD_ | _TBD_ | Notes ↔ Evidence Objects |
| Literature synthesis / cross-paper | _TBD_ | e.g. evidence synthesis if workspace strong | Synthesis workspace |
| Manuscript writing (grounded) | _TBD_ | e.g. Evidence → Writing → Reviewer | Grounded Writing |
| Publication readiness / revision | _TBD_ | e.g. Reviewer + evidence verification | Journal packs / revision |
| Long-term research continuity | ❌ expected until Memory | Future pillar | Research Memory (P6+) |
| Cross-corpus Knowledge Graph | ❌ expected until Graph | Future pillar | KG Product (P5+) |

---

## Predicted next frontier (hypothesis — confirm or reject after fill)

If critical daily workflows are strong but context switching still high (PDF, notes, synthesis, publication), next milestone is likely:

**Research Workspace & Publication**

* First-class PDF reader and annotation
* Evidence-linked notes
* Cross-paper synthesis and comparison
* Literature review workspace
* Publication preparation
* Revision workflows

Only after researchers are genuinely living inside Dhund: invest heavily in Knowledge Graph → Research Memory → Continuous Monitoring → Research Agents.

---

## Positioning / marketing claim gate

Do **not** position Dhund as a researcher’s **primary research workspace** (or market “replace Anara / SciSpace / Jenni”) until:

1. Critical daily workflows are ✅ or strong 🟡 with clear advantages documented above  
2. Context Switching Audit + Research Week Diary show researchers can stay for a real research week — with leaves mostly **legitimate**, not **forced**  
3. Research Session Completion KPI is strong with **real-user validation** (internal + 10–20 researchers) — not only engineering DoD  
4. Research Progress KPI shows real research advancement (not only retention)  
5. Cognitive Load Audit shows fewer / clearer decisions on critical paths  

Future pillars remaining ❌ does **not** block primary-workspace positioning if daily workflows hold.

---

## Outcome log

| Date | Decision |
|------|----------|
| _after #28 + validation_ | Next milestone = … (Workspace / pillar / other). Reasoning: … · Primary-workspace positioning allowed? Y/N · Session Completion: _n_/12 · Research Progress: _n_/5 · Cognitive load: ↑/↓/flat · Forced leaves remaining: … |

---

## Product Doctrine

```text
The purpose of Dhund is not to generate more AI content.

The purpose of Dhund is to help researchers think better,
work with evidence more effectively,
and complete more of their research without unnecessary context switching.

Every milestone should measurably improve at least one of:

• Research quality
• Research velocity
• Research confidence
• Research continuity

If a feature does not improve one of those outcomes,
it should not take priority over unfinished daily workflows.
```

**Operational checks (map to this review):**

| Outcome | Measured by |
|---------|-------------|
| Research continuity | Session Completion · Context Switching (forced leaves ↓) |
| Research velocity / quality | Research Progress KPI |
| Research confidence | Evidence trail · Reviewer · inspectable Analysis |
| Cognitive ease (supports all four) | Cognitive Load Audit |

This shifts focus from the software to the **research outcome**.
