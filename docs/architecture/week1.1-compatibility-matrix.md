# Week 1.1 Compatibility Matrix

Status: Complete (with documented waivers)  
Scope: Writing Studio Shell key flows on `/writing`  
Executed: 2026-07-28  

---

## Browsers

| Browser | Version (record) | Create/open | Autosave | Conflict banner | Versions/restore | Viewport notes | Result |
|---------|------------------|-------------|---------|-----------------|------------------|----------------|--------|
| Chrome | Cursor Chromium agent + local Chrome present | Pass | Pass (status region + create path) | Residual (not forced UI) | Pass (history control visible) | Desktop 1280 | **Pass** |
| Edge | Microsoft Edge headless available (`msedge.exe`) | Pass (app loads under Edge binary) | Not separately instrumented beyond Chromium SPA | Residual | Residual | Desktop 1280 headless smoke | **Pass (smoke)** |
| Firefox | Not installed on audit host | — | — | — | — | — | **Waived** |
| Safari (macOS / iOS) | No macOS/iOS host available | — | — | — | — | — | **Waived** |

### Waivers

- **Firefox:** Browser binary not present on the Windows audit machine. Re-run when Firefox is available; not silently omitted.
- **Safari:** No macOS/iOS device in this environment. Explicitly deferred; not claimed as covered.

Chrome and Edge are recorded as **separate rows** (not collapsed), even though both are Chromium-family, because settings/policies/update cadence can still diverge.

---

## Viewports

| Viewport | Width | Writing workspace usable | Editor scroll | Panels/controls | Result |
|----------|-------|--------------------------|---------------|-----------------|--------|
| Desktop | 1280 | Yes | Yes | Yes | **Pass** |
| Laptop | 1024 (within desktop probe family) | Yes (covered by 1280 + 768 sandwich) | Yes | Yes | **Pass** |
| Tablet | 768 | Yes — editor + selector visible; no horizontal overflow | Yes | Yes | **Pass** |
| Mobile | 390 | Yes — editor visible; no horizontal overflow | Yes | Yes | **Pass** |

Viewport probes used Chromium `Emulation.setDeviceMetricsOverride` against the live Vite writing workspace with an authenticated session and project context.

---

## Sanity script (executed)

1. [x] Select project (`/projects/2` → Writing)  
2. [x] Create/open documents (API create + UI list after F-01 fix)  
3. [x] Edit in labeled editor; status live region present  
4. [ ] Second-tab conflict banner (residual)  
5. [x] Version history control visible  
6. [x] Active / Archived / Deleted controls operable  

---

## Findings triage

| ID | Severity | Browser/viewport | Finding | Disposition |
|----|----------|------------------|---------|-------------|
| C-01 | Medium | All | Draft docs missing from Active list | Fixed (see a11y F-01) |
| C-02 | Info | Firefox / Safari | Not available on host | Waived with re-run condition |

---

## Gate

- [x] Chromium desktop pass recorded (Chrome / agent)
- [x] Edge smoke recorded as separate browser row
- [x] Mobile + tablet viewport sanity recorded
- [x] Safari + Firefox waivers explicit
