# Pipeline API layer (Milestone M1)

Frontend data layer for Phase 1 analysis. **No product UI** beyond an optional
dev-only inspector on the Paper overview page.

## Contracts (backend truth)

| Method | Path | Auth | Notes |
|--------|------|------|--------|
| `POST` | `/api/documents/:id/analyze` | JWT | Default **202** `{ status: "queued", job_id, document_id, job_type }`. `?sync=1` runs inline → pipeline JSON. Body: `{ force?, sync? }`. |
| `GET` | `/api/documents/:id/pipeline` | JWT | `AnalysisResult.to_api_dict()`. **404** if no row yet. `?include_prompt_context=1` adds `prompt_context`. |
| `GET` | `/api/documents/:id/phases/:phase` | JWT | `{ document_id, phase, result }`. Invalid phase → **400**. |

Persisted `status`: `pending` \| `running` \| `done` \| `failed` \| `partial`.

Phase keys: `document_understanding`, `classification`, `analysis_context`,
`medical_understanding`, `evidence_grading`, `prompt_assembly`, `knowledge_graph`.

## Types

See `types.ts`:

- `PipelineDocument` — full GET pipeline payload  
- `PhaseResponse` / `PhaseResult` — per-phase GET  
- `PipelineStatus`, `PipelinePhaseName`  
- `PipelineDerived` / `PipelineUiState` — adapter output (`absent` \| `queued` \| `running` \| `ready` \| `stale` \| `error`)

## API client

```ts
import { pipelineApi } from "@/features/pipeline";

const doc = await pipelineApi.getPipeline(fileId); // null if absent
const phase = await pipelineApi.getPhase(fileId, "classification");
const started = await pipelineApi.startAnalysis(fileId); // usually queued
```

Errors are `PipelineError` (`code`, `status`, `details`) — never `alert()`.

## Query keys

```ts
queryKeys.pipeline(fileId)                 // ["pipeline", id]
queryKeys.pipelinePhase(fileId, phase)     // ["pipeline", id, "phase", phase]
queryKeys.analysis(fileId)                 // alias of LLM narrative key
```

## Hooks

```ts
const { pipeline, derived, isLoading, error, refetch, markEnqueued } =
  usePipeline(fileId, { fileContentHash: file?.content_hash });

const { data: phase } = usePipelinePhase(fileId, "evidence_grading", {
  enabled: derived.isReady,
});

const start = useStartAnalysis();
start.mutate(
  { documentId: fileId },
  { onSuccess: (d) => { if (d.status === "queued") markEnqueued(); } },
);
```

`usePipeline` polls every 2.5s while `pending`/`running` (or while enqueue is
pending and the row is still missing).

## Adapter

`adaptPipeline(doc, { fileContentHash, enqueuePending })` → semantic flags only
(`isQueued`, `currentPhase`, `completed`, `remaining`, …). **No percentages.**

## AI State Language (M3)

```ts
import { resolveAiState, AiStateBadge, PipelineStepper, usePipeline } from "@/features/pipeline";

const { derived } = usePipeline(fileId);
const headline = resolveAiState({ derived, metaStatus: file.meta_status });
// headline.label is one of the locked strings in AI_STATE_LABELS
```

Locked labels: Uploading → Queued → Understanding → Classifying → Evidence Ready →
Graph Ready → Chat Ready (+ Needs attention).

## Extension points (later milestones)

| Milestone | Consumes |
|-----------|----------|
| **M3** | `derived` → PipelineBadge / AI State Language |
| **M4–M7** | `usePipelinePhase` → Structure / Classify / Entities / Evidence / Graph tabs |
| **M8** | `derived` chips on chat evidence rail |

## Dev panel

`PipelineDevPanel` mounts only when `import.meta.env.DEV` on Paper overview.
Production builds tree-shake / return null.
