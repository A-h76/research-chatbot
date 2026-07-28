# Week 1.1 Runtime Accessibility Audit

Status: Complete (with residual NVDA speech confirmation optional)  
Scope: Writing Studio Shell critical flows (`WritingPage` / `/writing`)  
Executed: 2026-07-28  
Environment: Local Vite `http://127.0.0.1:5173` + Flask (dev mode, `DEV_AUTO_LOGIN`)  
Agent browser: Cursor Chromium session  

---

## Critical flows

| Flow | Keyboard-only | Screen reader / live region | Result |
|------|---------------|-----------------------------|--------|
| Create / open document | Pass — New draft, document selector, title, editor in tab order | Pass — polite live region announced create (`Draft created`) | Pass |
| Edit + autosave status awareness | Pass — editor focusable, labeled | Partial — `role="status"` / `aria-live="polite"` present (`Saved`); intermediate Dirty/Saving not observed in this run | Pass with note |
| Conflict banner interaction | Partial — banner markup present in code; conflict UI not forced in this session | Structural alert still covered by Stage 4 | Deferred / residual |
| Version restore confirm | Pass — version history control reachable (`v1 · create`) | N/A this pass | Pass (reachability) |
| Archive / trash / recovery | Pass — Active/Archived/Deleted focusable; focus remained on lifecycle control after switch | Pass | Pass |

---

## Structural evidence (Stage 4)

From `tests/test_writing_accessibility.py`:
- Save/status live region present
- Conflict alert present with recovery copy
- Document selector + editor have accessible names

---

## Runtime checklist

### Keyboard-only

- [x] Tab order reaches writing controls (Skip → shell chrome → Draft/Export → Active/Archived/Deleted → Select writing document → New draft → transforms → editor)
- [x] No focus trap observed in writing workspace
- [x] Lifecycle controls (Active/Archived/Deleted) operable and retain focus after activation
- [x] Document selector and editor have accessible names in the a11y tree
- [ ] Conflict banner actions keyboard-operated (not exercised this session — residual)

### Screen reader / announcements

Tooling note: full **NVDA** speech output was not driven in the agent environment. DOM live-region behavior was verified instead.

- [x] Live regions present (`aria-live="polite"`, `role="status"`)
- [x] Create path updates a polite live region (`Draft created`)
- [x] Autosave status region present (`Saved`)
- [ ] NVDA spoken confirmation by human operator (optional residual — recommend 5-minute local NVDA pass)
- [ ] Conflict alert spoken (residual until conflict UI exercised)

### Reduced motion / contrast

- [x] Status text present (not color-only) for Saved
- [x] No motion-dependent writing controls observed for core create/edit path

---

## Findings triage

| ID | Severity | Finding | Disposition |
|----|----------|---------|-------------|
| F-01 | Medium | Active tab listed `status=active` only, but **New draft** creates `status=draft`, so drafts never appeared in the working list | **Fixed** in `WritingPage.tsx` — Active = working set (`draft` + `active`) |
| F-02 | Low | Intermediate autosave states (Dirty/Saving) not observed during automation typing; status region remained `Saved` | Accepted for Week 1.1 — region present; recommend NVDA confirm of state transitions |
| F-03 | Low | Conflict banner runtime path not exercised in browser session | Deferred — Stage 4 structural + API conflict storm covered; optional follow-up |

---

## Gate

- [x] Runtime keyboard audit completed
- [x] Runtime live-region / a11y-tree audit completed (NVDA speech optional residual)
- [x] Findings triaged (fix / accept / defer)
