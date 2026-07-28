# Phase 2.0 — Research Validation Protocol

**Status:** Kit complete · researcher **sessions after Phase 2.2**  
**Parent:** [`phase-2-writing-roadmap.md`](./phase-2-writing-roadmap.md)  
**Ops checklist:** [`phase-2.0-ops-readiness.md`](./phase-2.0-ops-readiness.md)  
**Type:** Product validation (first external users)  
**Not:** Endless dashboards · not “wait for Phase 2.5”

### Timing (revised)

Validation **tooling** is done. Do not expand it.

**Invite 5–10 researchers after Writing Shell (2.1) + Evidence Layer (2.2)** so the story they test is:

> Import → Analyse → Compare → Write with evidence

Until then: build SaaS-PK readiness + 2.1 + 2.2. Soft launch only after those sessions and critical fixes.

### Scope freeze

No new analytics products, feature-flag farms, or onboarding projects under the “2.0” label. SaaS billing/quotas live under [`public-saas-readiness-pk.md`](./public-saas-readiness-pk.md), not as Phase 2.0 scope creep.

---

## Goal

Learn whether Dhund’s **full differentiator** fits a real literature-review workflow — Library **and** Writing-with-evidence — before soft launch and before building Reviewer / heavy guided AI in isolation.

**Primary task for every participant:**

> Complete your literature review workflow using Dhund (import → ready papers → compare → draft with evidence where the studio allows).

Success is measured by **observed behaviour**, not star ratings.

---

## Who to invite (5–10)

Aim for mix, not clones:

| Role | Target count | Why |
|------|--------------|-----|
| PhD student | 3–4 | Core ICP; long lit reviews |
| Master’s student | 1–2 | Shorter cycle; less tool patience |
| Research assistant | 1–2 | Import/organise heavy |
| Professor / PI | 1–2 | Expects clarity, distrusts fluff |

Prefer people with a **live topic** and an existing Zotero/Mendeley/BibTeX library (≥30 papers ideal; ≥10 minimum).

---

## Session format

| | |
|--|--|
| Length | 45–60 minutes |
| Mode | Screen share + think-aloud · facilitator watches silently when possible |
| Environment | Production or stable staging with their own account |
| Recording | Optional; note-taking required either way |
| Incentive | Optional (coffee voucher / acknowledgment) — keep light |

**Facilitator rules**

1. Do **not** explain “Research Ready” unless they ask — first observe whether the UI teaches it.
2. Do **not** demo Compare before they explore Library — watch natural path.
3. Rescue only after 90+ seconds of stuckness, then note the rescue.
4. After the task, ask the debrief questions once — don’t lead during the task.

---

## Pre-session setup (you)

- [ ] Stable build with Phase 1c visible (Library Health strip, readiness badges, duplicates, attach PDF, sync)
- [ ] Worker healthy (import / phase1 jobs complete)
- [ ] Test account smoke: BibTeX import → attach PDF → readiness moves → Compare with 2 papers
- [ ] Participant has invite + login path (Google / magic link / whatever you use)
- [ ] Open a blank [session log](./phase-2.0-session-log-template.md) copy

**Suggested entry URL:** `/library`

---

## Task script (say this)

> You have about 45 minutes. Use Dhund as you would for a real literature review on **[their topic]**.  
> Import papers you already care about (Zotero, Mendeley, BibTeX/RIS, or Discover).  
> Organise enough that you could start writing a related-work section.  
> There is no wrong path — talk through what you’re looking for. I’ll stay quiet unless you’re stuck.

If they finish early:

> Before we stop — open Compare with a few papers you consider ready, then glance at Writing if you want. Tell me what you’d do next for a real manuscript.

---

## Observation checklist (watch, don’t ask yet)

Mark **Y / N / Partial** + timestamp notes. Full rubric in the [session log template](./phase-2.0-session-log-template.md).

### A — Import & Library

| # | Signal | Pass if |
|---|--------|---------|
| A1 | Finds Library / Connect | Reaches import without facilitator |
| A2 | Completes an import | ≥1 paper in library from their source |
| A3 | Notices metadata-only vs PDF | Mentions stub / “no PDF” / attach, or uses Attach PDF |
| A4 | Attaches or uploads PDF | At least one stub becomes a real file **or** they upload PDFs directly |
| A5 | Understands analysis wait | Expects processing; doesn’t assume instant “ready” without evidence |

### B — Research Ready & Health

| # | Signal | Pass if |
|---|--------|---------|
| B1 | Notices Health / readiness UI | Looks at strip or badges without being told |
| B2 | Can explain Research Ready | In their words: PDF + analysed/indexed / usable for research — not “uploaded” |
| B3 | Health is useful or ignored | Note which; both are data |

### C — Duplicates & organisation

| # | Signal | Pass if |
|---|--------|---------|
| C1 | Sees duplicate suggestions | If panel appears with groups |
| C2 | Trusts / acts on dupes | Merges, dismisses thoughtfully, or explains why wrong |
| C3 | Uses project or collection | Optional — note if natural |

### D — Compare & synthesis path

| # | Signal | Pass if |
|---|--------|---------|
| D1 | Discovers Compare | Finds `/research/compare` or toolbar entry |
| D2 | Runs Compare on ready papers | Selects ≥2 analysed papers |
| D3 | Compare before “project” | Note order: Compare ↔ Project creation |

### E — Writing desire (critical for 2.1+)

| # | Signal | Pass if |
|---|--------|---------|
| E1 | Wants to write in-product | Says they’d draft here / asks for Word-like space / opens `/writing` |
| E2 | Seed preference | Compare/gaps vs blank page vs export elsewhere |
| E3 | Contradiction trust | Reaction to “contradicting paper” idea (probe in debrief if not spontaneous) |

---

## Debrief (5–8 minutes, after task)

Ask in this order. Record verbatim quotes.

1. In your own words, what does **Research Ready** mean here?
2. What did you expect to happen after importing from Zotero/BibTeX?
3. Where did you feel stuck or unsure?
4. Would you start a draft **inside Dhund** next, or export and leave? Why?
5. If Dhund suggested a paper that **contradicts** a paragraph you wrote, would that help or annoy you?
6. What one change would make this usable for your next real review?

---

## Gate criteria (when 2.0 can close)

Run **≥5 completed sessions** (target 5–10). Then score:

### Hard fail → fix Phase 1 before 2.2

Any of these in **≥40%** of sessions:

- Cannot complete an import without heavy rescue
- Never understand Research Ready even after debrief prompt + UI in view
- Systematically skip PDF attach and assume metadata = analysed
- Duplicate merge would destroy the “keep” PDF / they refuse all suggestions as wrong
- Worker/jobs leave papers stuck pending with no recovery path they can see

### Soft fail → fix or explicitly defer before 2.2

- Health strip ignored by everyone (labeling / placement issue)
- Compare never discovered (IA issue — may fix in 2.1 shell nav)
- Everyone exports immediately and rejects in-app writing (revisit 2.1 value prop)

### Pass → unlock 2.1 (shell), then 2.2 only after Phase 1 fixes from this round are done

- ≥5 sessions logged
- Import + at least one path to PDF/analysis works for majority
- Research Ready comprehensible to majority after using the product (debrief)
- Writing desire or clear “I’d write here if X” list documented
- Friction list triaged: **Fix now** / **Defer with reason** / **Ignore**

**Do not start Evidence Layer (2.2) until hard fails are fixed or waived in writing.**

---

## Outputs of Phase 2.0

1. Filled [participant tracker](./phase-2.0-participant-tracker.md)
2. One session log per person (copy of template)
3. **Friction backlog** (table below, living doc — update as you go)
4. Go / no-go note for Phase 2.1

### Friction backlog (start empty)

| ID | Observation | Severity | Decision | Owner | Notes |
|----|-------------|----------|----------|-------|-------|
| F-001 | | hard / soft / note | fix now / defer / ignore | | |

---

## Invite email (copy)

**Subject:** 45-min research workflow session on Dhund (literature review)

Hi [Name],

I’m validating Dhund — a research workspace for importing your library, analysing papers, and preparing a literature review — with a small group of researchers before we build the writing studio.

**Ask:** One 45–60 minute screen-share session. Bring a real topic and, if you can, a Zotero/Mendeley/BibTeX export or a folder of PDFs. We’ll watch how the product supports *your* workflow (not a scripted demo).

No preparation slides. Optional recording. Feedback stays confidential.

If you’re willing, reply with 2–3 times that work in the next two weeks.

Thanks,  
[You]

---

## Facilitator one-pager (print / second screen)

```
URL: /library
Task: lit review workflow on THEIR topic
Quiet unless 90s stuck
Watch: import → PDF → Ready → dupes → Compare → want to write?
Debrief: Ready meaning · import expectation · stuck · write here? · contradiction · one change
Log: Y/N + quotes + rescues
```

---

## Immediate next actions

1. **Build track:** Public SaaS readiness (PK) ∥ Phase **2.1** Writing shell → Phase **2.2** Evidence.  
2. Keep validation kit ready; do **not** expand Phase 2.0 tooling.  
3. Deploy/smoke on dhund.com when billing + Writing MVP are ready for outsiders.  
4. **Then** invite 5–10 researchers (this protocol); fill tracker / friction backlog.  
5. Fix critical issues → Founding soft launch → grow 2.3–2.5 with feedback.

**Do not** market loudly before 2.2. **Do not** wait for 2.5 / Teams / JazzCash merchant API before the first 5–10 users.

---

*Phase 2.0 starts when the first invite is sent — not when Writing Studio code lands.*
