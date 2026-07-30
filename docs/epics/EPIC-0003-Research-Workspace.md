# EPIC-0003 — Research Workspace

| Field | Value |
|-------|-------|
| **Status** | Ready after EPIC-0001 |
| **Priority** | P0 shell for research OS |
| **Depends on** | EPIC-0001; parallel with EPIC-0002 |
| **IDD** | 0003 API · 0004 Frontend · 0007 Auth |
| **Surfaces** | Home, Projects, Library, Paper reader, Search, Integrations |

---

## Intent

Ship the **application shell** where researchers live day-to-day—without depending on Writing/RI completion. Library and Papers must feel like a Research OS, not a file dump.

---

## Outcomes

1. Auth-gated SPA boot stable  
2. Projects CRUD + current project context  
3. Library list/upload/import empty states per vision  
4. Paper overview with readiness + pipeline progressive loading  
5. Search (library + discover) with glossary-safe copy  
6. Zotero/Mendeley connection status visible  

---

## Tickets — Developer A

| ID | Ticket | DoD |
|----|--------|-----|
| A-301 | Papers/files list API stable filters + pagination envelope | Matches IDD; ownership |
| A-302 | Upload façade notes / dual-route parity doc | Same job outcomes session vs JWT |
| A-303 | Pipeline status endpoint reliability | FE can poll phases |
| A-304 | Library connections + import error codes | `dependency_unavailable`, OAuth messaging |
| A-305 | Search API kind filters | Documented in gap list |

## Tickets — Developer B

| ID | Ticket | DoD |
|----|--------|-----|
| B-311 | AppShell IA: Home · Projects · Library · Research · Writing | Per UI vision; Ask Dhund demoted |
| B-312 | Library empty + import CTAs | Upload, Zotero, Mendeley, DOI, PMID, projects |
| B-313 | Paper overview tabs + readiness UX | Extract entry point wired to EPIC-0002 when ready |
| B-314 | Integrations status in sidebar | Connection dots |
| B-315 | Search page glossary copy | No Thinking/Generating |
| B-316 | Design system tokens (teal, type) applied to shell | Figma → code consistency |
| B-317 | Confirm dialogs / skeletons for library destructive ops | Calm UX |

## Tickets — Sync

| ID | Ticket | DoD |
|----|--------|-----|
| A+B-320 | Staging: new project → upload → see Research Ready | Checklist |

---

## Non-goals

- Grounded writing (0004)  
- Reviewer accordion (0005)  
- Marketing Jinja redesign (separate)  

---

## Exit criteria

- [ ] Researcher can organize papers in a project without Writing  
- [ ] Empty/loading/error states complete for Library + Paper  
- [ ] Auth failure → `/login` reliable  
- [ ] Ready to attach Evidence Inspector (0002) and Writing (0004)
