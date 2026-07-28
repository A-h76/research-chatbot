# Soro Product Specification

**Version:** 1.0  
**Status:** Locked — baseline for frontend implementation  
**Effective date:** 2026-07-26  
**Product:** Soro  

This file is the **index** for Product Specification v1.0. The documents listed below are the authoritative product, UX, and design contracts for the first implementation phase. Implementation work should cite this version (e.g. “implements Product Spec v1.0 §…”) and not invent competing navigation, AI-state labels, or visual language without a version bump.

---

## Spec set (v1.0)

| # | Document | Role in v1.0 |
|---|----------|----------------|
| 1 | [`UI-State.md`](UI-State.md) | **Current-state audit** — what exists today, gaps vs backend, scores, top issues |
| 2 | [`UI-Architecture.md`](UI-Architecture.md) | **Target product & UX architecture** — vision, personas, journeys, IA, screens, data/state, roadmap milestones |
| 3 | [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md) | **Visual & interaction language** — tokens, components contracts, **AI State Language** (incl. Queued), a11y, anti-patterns |

Together these three documents are **Product Specification v1.0**.

---

## Supporting references (not part of the v1.0 product lock)

These inform engineering readiness but are **not** product UX contracts:

| Document | Role |
|----------|------|
| [`Dhund-Flow/PROJECT_STATUS.md`](Dhund-Flow/PROJECT_STATUS.md) | Executive engineering status (canonical) |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Root pointer → Dhund-Flow |
| [`docs/SECURITY_BASELINE_PR1.md`](docs/SECURITY_BASELINE_PR1.md) … [`PR4`](docs/SECURITY_BASELINE_PR4.md) | Security hardening baselines |
| Backend Phase 1–2 packages + APIs | Stable **capability** contracts the UI must reveal |

---

## Locked decisions in v1.0 (summary)

1. **Product feel:** Research instrument — inspectable pipeline, not PDF-chatbot.  
2. **IA:** Primary nav ≤4 (Home, Library, Projects, Chat) + Research group; Paper Workspace tabs.  
3. **Upload home:** Library primary; Composer secondary.  
4. **AI State Language (exact labels, in order):**  
   **Uploading → Queued → Understanding → Classifying → Evidence Ready → Graph Ready → Chat Ready**  
   (+ **Needs attention**). Same pattern on Library, Paper, Projects, Dashboard.  
5. **Forbidden progress copy:** “Processing…”, “Done”, “Working…”, and other vague substitutes.  
6. **Design system:** Ink neutrals, teal-ink signal accent, light-first; violet/legacy AI chrome is migration debt.  
7. **Design system completeness:** Feature-complete for first implementation phase (see Design System §17).

---

## Versioning policy

| Change type | Action |
|-------------|--------|
| Typos, clarifications that don’t change behavior | Patch note under same **1.0** (optional `1.0.1` in changelog below) |
| New screen, nav change, new AI state, token/brand change | Bump to **1.1** / **2.0** and update this index |
| Implementation PRs | Must not contradict v1.0 without an explicit spec revision |

### Changelog

| Version | Date | Notes |
|---------|------|-------|
| **1.0** | 2026-07-26 | Initial product lock: UI-State + UI-Architecture + Design System (incl. Queued AI state) |

---

## How to use

- **Product / design:** Treat Architecture + Design System as the source of truth for *what to build*.  
- **Engineering:** Use UI-State for gap prioritization; implement Architecture milestones (M0–M12) with Design System tokens/states.  
- **Review:** PRs that change user-visible status labels or primary IA should be rejected if they diverge from v1.0 without a spec bump.

---

*Soro Product Specification v1.0 — locked baseline.*
