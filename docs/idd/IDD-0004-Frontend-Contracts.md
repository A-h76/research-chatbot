# IDD-0004 — Frontend Contracts

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Owner** | Developer B |
| **Depends on** | [IDD-0002](./IDD-0002-Domain-Model.md), [IDD-0003](./IDD-0003-API-Contracts.md) |

This document defines **page-level** data needs so Backend can mock/serve and Frontend can build without waiting on AI internals.

---

## 1. Cross-cutting UI rules

| Concern | Contract |
|---------|----------|
| Boot | `GET /api/me` — fail → hard navigate `/login` |
| Loading | Prefer structural skeletons (not spinners-only); never blank `#` sections |
| Empty | Always offer next workflow action (Upload, Import, Extract, Write) |
| Errors | Toast + inline; map `error` code to copy (IDD-0007) |
| Optimistic | Allowed for renames, accept/reject evidence, autosave; rollback on failure |
| Caching | TanStack Query; keys in §8 |
| Evidence UI | Never show raw “LLM said”; show EvidenceObjects + confidence |
| Progress copy | Research stages only—no “Thinking…” / “Generating…” |

---

## 2. Pages

### 2.1 Home / Dashboard (`/home`)

| | |
|--|--|
| **APIs** | `GET /api/me`, projects list or hub summary, optional library health |
| **Shape** | Counts: papers, research_ready, evidence accepted, open drafts |
| **Loading** | Dashboard skeleton |
| **Empty** | CTA → Library import / New project |
| **Error** | Retry card |
| **Optimistic** | None required |
| **Cache** | `["dashboard", userId]` stale 60s |

---

### 2.2 Projects (`/`, `/projects/:id`)

| | |
|--|--|
| **APIs** | CRUD `/api/projects*`, hub, questions, project research presets |
| **Shape** | `Project`, hub widgets |
| **Loading** | List skeleton |
| **Empty** | Create project |
| **Error** | Inline |
| **Optimistic** | Create/rename project |
| **Cache** | `queryKeys.projects`, invalidate on mutation |

---

### 2.3 Library (`/library`)

| | |
|--|--|
| **APIs** | `GET /api/files`, upload, library connections/import, delete, facets |
| **Shape** | `Paper[]` + `total` + readiness |
| **Loading** | `LibraryPapersSkeleton` |
| **Empty** | Start research CTAs (Upload, Zotero, Mendeley, DOI, PMID, Projects)—per UI vision |
| **Error** | Banner + retry |
| **Optimistic** | Tag edits; not file delete until confirmed |
| **Cache** | `["files", filters, projectId, page]` |

**Integrations panel:** `GET /api/library/connections` — connection dots.

---

### 2.4 Paper Reader / Overview (`/papers/:paperId`)

| | |
|--|--|
| **APIs** | `GET /api/files/:id`, pipeline status, analysis tabs, `POST .../evidence/extract`, evidence list |
| **Shape** | `Paper`, pipeline DTO, optional `PaperAnalysis`, `EvidenceObject[]` |
| **Loading** | Tab skeletons; pipeline progressive |
| **Empty** | Not ready → show processing stages |
| **Error** | Phase failure with retry |
| **Optimistic** | None for extract (show ResearchProgressStage) |
| **Cache** | `["file", id]`, `["pipeline", id]`, `["evidence", projectId, paperId]` |

**Extract button:** disabled unless `research_readiness === research_ready` and `project_id` set.

---

### 2.5 Evidence Inspector (panel / drawer)

| | |
|--|--|
| **APIs** | `GET /api/evidence/:id`, `POST /api/evidence/explain`, `POST .../reviews` |
| **Shape** | `EvidenceObject`, ExplainDTO |
| **Loading** | Panel skeleton |
| **Empty** | “Select a citation” |
| **Error** | Explain failed → retry |
| **Optimistic** | Accept/reject with rollback |
| **Cache** | Invalidate project evidence lists on review |

**Signature interaction:** citation click → Inspector (UI vision).

---

### 2.6 Writing Workspace (`/writing`)

| | |
|--|--|
| **APIs** | documents CRUD/autosave/versions; `POST /api/evidence/writing`; bindings; export |
| **Shape** | `WritingDocument`, `GroundedWritingResult`, bindings |
| **Loading** | Outline usable first; Evidence rail may stage-load |
| **Empty** | Prompt to select project + accept evidence |
| **Error** | `blocked` is **not** a transport error—show insufficient evidence CTA |
| **Optimistic** | Autosave body; grounded insert only after `status=ok` |
| **Cache** | `["writing","documents", projectId]`, `["writing","document", id]` |

**Layout:** Outline | Manuscript | Evidence.  
**Progress:** `ResearchProgressStage` with lit-review stages while `POST /evidence/writing` pending.  
**Confidence:** show metrics from result; hide vanity metrics.

---

### 2.7 Reviewer UI (within Writing)

| | |
|--|--|
| **APIs** | Embedded in `GroundedWritingResult.review`; future `GET .../reviewer-runs` |
| **Shape** | `ReviewerFinding[]` |
| **Loading** | Accordion placeholder |
| **Empty** | “No issues” |
| **Error** | Missing review → degrade gracefully |
| **Optimistic** | N/A |
| **Cache** | Tied to last grounded result |

---

### 2.8 Search (`/search`)

| | |
|--|--|
| **APIs** | `POST /api/search`, discover `GET /api/discover`, optional ask-from-library |
| **Shape** | `SearchResult[]`, Discover works |
| **Loading** | “Searching library…” (not Thinking) |
| **Empty** | Soft empty + discover CTA |
| **Error** | discover_unavailable soft fail |
| **Cache** | `["search", q, kinds]`, `["discover", q, page]` |

---

### 2.9 Research Compare (`/research/compare`)

| | |
|--|--|
| **APIs** | compare / gaps endpoints |
| **Shape** | comparison DTO |
| **Loading** | Workbench skeleton |
| **Empty** | Select ≥2 papers |
| **Error** | Retry |
| **Cache** | `["comparison", paperIds]` |

---

### 2.10 Export

| | |
|--|--|
| **APIs** | export document / poll export job |
| **Shape** | file download or markdown string |
| **Loading** | Button busy + job poll |
| **Empty** | N/A |
| **Error** | Show `failed` reason |
| **Optimistic** | No |

---

### 2.11 Settings

| | |
|--|--|
| **APIs** | profile, data export/delete, models list |
| **Cache** | `queryKeys.me`, settings keys |

---

## 3. TypeScript interfaces (frontend-safe)

> Hand-maintained or generated from OpenAPI. **Do not** invent runtime code here.

```ts
/** Shared */
export type ConfidenceBand = "low" | "moderate" | "high";
export type EvidenceStatus = "candidate" | "accepted" | "rejected" | "superseded";
export type ResearchReadiness =
  | "uploaded"
  | "processing"
  | "research_ready"
  | "failed"
  | "archived";

export interface User {
  id: number;
  email: string;
  name: string;
  picture: string | null;
  plan: string;
  is_admin?: boolean;
}

export interface Project {
  id: number;
  name: string;
  emoji?: string | null;
  instructions?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AuthorRef {
  name: string;
  orcid?: string | null;
  affiliation?: string | null;
}

export interface Paper {
  id: number;
  /** @deprecated prefer paper semantics; same as id in files API */
  file_id?: number;
  user_id: number;
  project_id: number | null;
  title: string | null;
  name: string;
  authors: AuthorRef[] | string | null;
  year: number | null;
  venue: string | null;
  doi: string | null;
  research_readiness: ResearchReadiness | string | null;
  research_readiness_label?: string | null;
  import_source?: string | null;
  created_at: string;
}

export interface EvidenceObject {
  id: number;
  project_id: number;
  paper_id?: number;
  file_id: number;
  quote: string | null;
  claim: string | null;
  finding?: string | null;
  evidence_type?: string | null;
  confidence_band: ConfidenceBand;
  status: EvidenceStatus;
  page_start?: number | null;
  page_end?: number | null;
  supports?: unknown;
  contradicts?: unknown;
  limitations?: unknown;
  pipeline_version: string;
  content_hash?: string;
  supersedes_id?: number | null;
  provenance?: Record<string, unknown>;
  created_at?: string;
}

export interface EvidenceQuery {
  intent:
    | "support_sentence"
    | "answer_question"
    | "review_coverage"
    | "compare_topic"
    | "list_project";
  scope: {
    project_id: number;
    file_ids?: number[] | null;
    document_id?: number | null;
  };
  filters?: {
    status?: EvidenceStatus[];
    confidence_bands?: ConfidenceBand[];
  };
  anchors?: Record<string, unknown>;
  section_type?: WritingSectionType;
  ranking_strategy?: string;
  result_limit?: number;
}

export type WritingSectionType =
  | "support_sentence"
  | "introduction"
  | "literature_review"
  | "discussion"
  | "clinical_summary"
  | "research_gap"
  | "executive_summary";

export interface WritingDocument {
  id: number;
  project_id: number;
  title: string;
  body: string;
  status: string;
  updated_at?: string;
}

export interface ReviewerFinding {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  section_id?: string | null;
  evidence_ids?: number[];
}

export interface GroundedWritingResult {
  status: "ok" | "blocked";
  section_type?: WritingSectionType | string;
  paragraph?: string;
  citations: Array<{ evidence_object_id: number; label?: string }>;
  metrics?: {
    grounding_pct?: number;
    reviewer_pass_rate?: number;
    citation_count?: number;
  };
  review?: {
    reviewer_version: string;
    issues: ReviewerFinding[];
  };
  warnings?: string[];
  disclaimer?: string;
  writing_version: string;
  blocked_reason?: string;
  mode?: string;
}

export interface CitationBinding {
  id: number;
  document_id: number;
  evidence_object_id: number;
  block_id?: string | null;
}

export interface SearchResult {
  kind: "paper" | "evidence" | "note" | "citation" | "chat" | "project";
  ref_id: number;
  title: string;
  snippet?: string | null;
  score?: number | null;
  project_id?: number | null;
  document_id?: number | null;
}

export interface JobStatus {
  id: number;
  job_type: string;
  status: "pending" | "running" | "done" | "failed";
  error?: string | null;
  updated_at?: string;
}

export interface ExportJob {
  id: number;
  document_id: number;
  format: string;
  status: "pending" | "running" | "done" | "failed";
  download_url?: string | null;
  error?: string | null;
}

export interface ApiErrorBody {
  error: string;
  detail?: string;
  fields?: Record<string, string[]>;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
```

---

## 4. Query key conventions

```ts
["me"]
["projects"]
["project", projectId]
["files", { projectId, filters, page }]
["file", paperId]
["pipeline", paperId]
["evidence", projectId, filters]
["evidence-object", id]
["writing", "documents", projectId]
["writing", "document", id]
["search", q, kinds]
["jobs", jobId]
["library-connections"]
```

---

## 5. Mock strategy (unblocks B)

Provide fixtures under `frontend/src/mocks/idd/`:

- `papers.json`, `evidence.json`, `grounded-ok.json`, `grounded-blocked.json`
- MSW handlers matching IDD-0003 routes

Definition of ready-for-UI: mocks satisfy loading/empty/error/optimistic cases above.
