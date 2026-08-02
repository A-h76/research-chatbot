# Research Ecosystem Masterplan

**Document:** `10-RESEARCH-ECOSYSTEM-MASTERPLAN.md`  
**Date:** 2026-08-02  
**Pillar:** Discovery + Monitoring — how every integration **changes the product**  
**Timing:** Guides P1–P2 engineering and all future connectors.

**Related:** [05-RESEARCH-OS-VISION.md](05-RESEARCH-OS-VISION.md) · [04-RESEARCH-OS-ROADMAP.md](04-RESEARCH-OS-ROADMAP.md) · `backend/library/adapters/` · `backend/scholarly/` · `worker.py`

---

## 1. Doctrine

Integrations are not logo badges. Each connector must answer:

| Question | Required answer |
|----------|-----------------|
| **Why does it exist?** | Which lifecycle step it strengthens |
| **Workflow** | End-to-end researcher path |
| **Backend** | Module / tables extended (not duplicated) |
| **OAuth / auth** | Protocol + token storage |
| **Sync** | Full / incremental / webhook / folder watch |
| **Workers** | Which HANDLER jobs |
| **Knowledge Graph** | What nodes/edges it contributes |
| **Evidence** | How extract/review is triggered |
| **Writing** | How drafts/cites benefit |
| **Automation** | Watches, agents, notifications |
| **Future extensions** | Honest next steps |

**Engineering rule (locked):** Extend `ImportAdapter`, `backend/scholarly/`, `HANDLERS`, and a thin Settings Integrations facade. **No** greenfield `backend/integrations/` with duplicate token/sync tables.

---

## 2. Ecosystem map by lifecycle

| Lifecycle step | Connectors (now → next) |
|----------------|-------------------------|
| Discovery | OpenAlex, Semantic Scholar, Crossref → **PubMed, arXiv, Europe PMC** |
| Import | Upload, BibTeX/RIS, Zotero, Mendeley → **Drive, Dropbox, OneDrive** |
| Identity | Google auth → **ORCID** |
| Evidence / KG / Memory | All imports feed the same pipeline |
| Writing / Publishing | Export BibTeX; later Docs/Notion bi-sync |
| Monitoring | Sync runs → folder watch → topic watch → Agents |

---

## 3. Provider blueprints

### 3.1 Zotero — Live (metadata); PDF pull incomplete

**Why:** Researchers already live in Zotero; Dhund must deepen that library into Evidence → Graph → Writing.

**Workflow**

```text
Connect → Collections → Import / Sync metadata
    → (P1) PDF pull → Import job → Analysis → Evidence
    → Knowledge Graph → Writing → Export (BibTeX back optional later)
```

| Layer | Plan |
|-------|------|
| Backend | `ZoteroAdapter`, `library_connections`, `LibrarySyncRun` |
| OAuth | OAuth1; tokens `enc:v1:` |
| Sync | Incremental metadata today; move to worker `library_sync` |
| Workers | `library_sync` (new), then `import` for PDFs |
| KG | Paper nodes + collection membership; citation edges when DOI enrich |
| Evidence | Auto or prompted `evidence_extract` after Research Ready |
| Writing | Library scope → WI |
| Automation | Periodic sync; conflict protect research assets |
| Future | Write-back notes; group libraries; better pagination |

---

### 3.2 Mendeley — Live (metadata); PDF pull incomplete

**Why:** Same as Zotero for Mendeley-native labs.

**Workflow** — same shape as Zotero (`MendeleyAdapter`, OAuth2).

| Future | Folders→collections polish; PDF `import_files`; worker sync |

---

### 3.3 BibTeX / RIS — Live

**Why:** Lowest-friction import without OAuth.

**Workflow**

```text
Upload bibliography → Normalize → Library stubs
    → Attach PDFs → Evidence → Writing
```

| Workers | Parse in-request or small import job; PDFs via attach/upload |
| Future | Round-trip export fidelity tests |

---

### 3.4 OpenAlex / Crossref / Semantic Scholar — Live (soft-fail)

**Why:** Discover + metadata enrich without leaving Dhund.

**Workflow**

```text
Discover search → Import stub → Enrich DOI → Analysis → Evidence
```

| Backend | `backend/scholarly/*` + Discover routes (route through adapters) |
| KG | Citation / related-work edges |
| Future | Always via adapter; circuit breakers already exist |

---

### 3.5 PubMed — Planned (P2)

**Why:** Biomedical discovery is incomplete if OpenAlex is the only path; PMID workflows are native to life sciences.

**Workflow**

```text
Search PubMed → Import → Compare / Evidence extract
    → Update Memory (“watched query hit”) → Writing / Review
```

| Layer | Plan |
|-------|------|
| Backend | `backend/scholarly/pubmed.py` (NCBI E-utilities / API key) |
| OAuth | API key / email (NCBI), not user OAuth |
| Sync | Search-on-demand; optional saved query watch |
| Workers | Import enqueue; later `topic_watch` |
| KG | MeSH / concept nodes; citation PMIDs |
| Evidence | Same extract pipeline |
| Writing | Scope by PMID set |
| Automation | Saved search → notify → Memory |
| Future | MyNCBI link; full-text PMC when OA |

---

### 3.6 arXiv / Europe PMC — Planned (P2)

**Why:** Preprints and EU/PMC full text.

**Workflow**

```text
Search → Import PDF/source → Analysis → Evidence → Memory
```

| Backend | Scholarly clients; rate limits |
| KG | Version lineage (arXiv versions) |
| Automation | Category watch |

---

### 3.7 Google Drive — Planned (P2)

**Why:** Labs drop PDFs in folders; Dhund should notice without manual upload.

**Workflow**

```text
Connect folder → Folder watch → New PDF
    → Import → Analysis → Evidence → Notify → Memory
```

| Layer | Plan |
|-------|------|
| Backend | Drive `ImportAdapter` or storage watcher service |
| OAuth | Google OAuth (Drive scope); sealed tokens |
| Sync | Changes.list / push webhook when available |
| Workers | `drive_watch` / `import` |
| KG | File→project edges |
| Evidence | Auto-queue extract optional (flagged) |
| Writing | New evidence available in desk |
| Automation | Core monitoring story |
| Future | Shared drives; Doc export bi-sync (later) |

---

### 3.8 Dropbox / OneDrive — Planned (after Drive)

**Why:** Same folder-watch product job for other campuses.

**Workflow** — identical to Drive with provider-specific OAuth/API.

---

### 3.9 ORCID — Planned (P2.5)

**Why:** Researcher identity; claim works; reduce duplicate authors in Graph.

**Workflow**

```text
Connect ORCID → Import works list → Match library → Author graph enrichment
```

| OAuth | ORCID OAuth2 |
| KG | Canonical author nodes |
| Future | Auto-claim new works → Memory |

---

### 3.10 Notion / Google Docs — Deferred (P4+)

**Why:** Writing bi-sync for labs that draft outside Dhund — **after** grounded export trust.

**Workflow**

```text
Export grounded MD → (later) sync Doc
    → Comments back optional
```

| Rule | Dhund remains source of evidence truth; Docs are presentation |

---

### 3.11 Slack / Teams / Webhooks — Deferred (P4 / Enterprise)

**Why:** Notify when extract completes, Drive drops PDF, Reviewer fails export.

**Workflow**

```text
Event (outbox) → Signed webhook / Slack message → Deep link to Inspector
```

---

### 3.12 MCP / Zapier / Public API — Deferred (Enterprise E1+ / P4)

**Why:** External automation into the same Evidence loop.

**Workflow** — API key → constrained endpoints (import, search memory, enqueue extract).  
**Forbidden:** unconstrained prompt execution without Evidence policy.

---

## 4. Template for every new integration (copy this)

```markdown
### Name

**Why:** …
**Lifecycle steps:** Discovery | Import | Identity | Monitor | Publish

**Workflow**
\`\`\`text
…
\`\`\`

| Layer | Design |
|-------|--------|
| Backend | |
| OAuth | |
| Sync | |
| Workers | |
| Knowledge Graph | |
| Evidence | |
| Writing | |
| Automation | |
| Future | |

**Live / Soon / Not planned:** …
**Depends on eng phase:** P1 | P2 | P4 | E1 …
```

---

## 5. Settings Integrations catalog (product)

Single page listing every provider with:

- Status: **Live** / **Soon** / **Not planned**  
- Capabilities: OAuth, sync, PDF, watch, write-back  
- Last sync / errors  
- Connect / Disconnect  

Landing Ecosystem section must **match this catalog** — no logo without a row.

---

## 6. Priority order (product impact)

1. Zotero/Mendeley **PDF + worker sync** (complete what we claim)  
2. Settings catalog honesty  
3. PubMed  
4. Google Drive watch  
5. arXiv / Europe PMC  
6. ORCID  
7. Dropbox / OneDrive  
8. Docs/Notion bi-sync  
9. Slack/webhooks  
10. MCP/Zapier  

---

## 7. Success metrics

| Metric | Meaning |
|--------|---------|
| % of EvidenceObjects from connected sources | Ecosystem feeds the OS |
| Sync success rate / time | Durability |
| Folder-watch → Research Ready latency | Monitoring works |
| Zero Live logos without working path | Marketing honesty |

---

## 8. Sequencing vs other pillars

```text
P1  Finish Zotero/Mendeley + catalog
P2  PubMed + Drive (+ arXiv/ORCID)
P5  Graph consumes citation/author edges from connectors
P6  Memory stores sync/watch episodes
P7  Monitoring Agent owns watches
E1  API keys for external ecosystem apps
```
