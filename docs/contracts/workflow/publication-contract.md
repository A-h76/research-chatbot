# WF-005 — Publication Contract

**Status:** Frozen (Workflow Contracts v1.0) — **MVP surface**  
**contracts_version:** `1.3.0`  
**Workflow step:** `Publication` (journey terminal; engine may track via Review complete + export events)  
**Source of truth:** Export / share / download paths under Writing + Workspace (extend here when adding surfaces)  
**Freeze pack:** [../WF-v1.0-COMPLETE-FREEZE.md](../WF-v1.0-COMPLETE-FREEZE.md)

Publication is the **exit** of the research journey: artifacts leave Dhund or become shareable snapshots. Product depth may grow; **boundaries** below are frozen so exports do not fork Evidence/Writing rules.

---

## 1. Input

| Kind | Required | Notes |
|------|----------|--------|
| Project / document scope | yes | What is being published |
| Authz | yes | Owner (or future share ACL — additive) |
| Artifact source | yes | Writing draft, evidence matrix export, bibliography, … |

**Entry points (many):** markdown/CSV/matrix export, document download, future share links — each must read from canonical Writing/Evidence artifacts, not a shadow copy.

---

## 2. Output

| Artifact | Meaning |
|----------|---------|
| Export bytes / file | Deterministic render of canonical state |
| Optional provenance stamp | versions, evidence ids, pipeline labels when applicable |
| Instrumentation | workflow breadcrumb `export_completed` (Phase A.6) when wired |

Publication **does not** create a second Evidence store or invent citations at export time.

---

## 3. Invariants

1. **Export is a projection** — never a parallel corpus; regenerating export from the same inputs must not invent new evidence.
2. **Citations remain Evidence-backed** — bibliography/export must use A-402 citation identity (`evidence_id` / `file_id`).
3. **One export policy per format family** — shared serializers (matrix CSV/MD, etc.); do not reimplement RI serializers inside a connector.
4. **No silent mutation** — publishing must not change EvidenceObject status as a side effect unless the user explicitly reviews.
5. **Honesty** — if a format is “Soon,” Ecosystem catalog must not claim Live (Ecosystem UX rule).
6. Domain Event Bus: only add a `PublicationCompleted` (or similar) via catalog registration + ADR-level name freeze — do not overload UI analytics.

---

## 4. Events

| Domain / workflow | When |
|-------------------|------|
| Workflow breadcrumb `export_completed` | Export succeeds (instrumentation catalog) |
| Future domain event | Only after name added to `DOMAIN_EVENT_NAMES` |

| Workflow step | Transition |
|---------------|------------|
| Journey complete | Review completed + optional export; Publication is the product terminal, not a second AI agent |

---

## 5. Ownership

| Owns | Does not own |
|------|----------------|
| **Writing / Workspace** — export renderers and download routes | Evidence extract; Import spine |
| **Trust** — future public share ACL / audit | Provider OAuth |

**PR gate:** A second “export this project’s evidence/writing” stack that re-derives claims outside EvidenceObjects requires ADR + retirement plan.

---

## Honest gaps (named)

- Engine step list today ends at `Review` (`RESEARCH_PAPER_STEPS`); Publication is contracted as the **product terminal** and may be added as an engine step in a minor, additive bump.
- Share-to-web / DOI deposit are **not** in v1.0 — additive product work under this contract’s invariants.
