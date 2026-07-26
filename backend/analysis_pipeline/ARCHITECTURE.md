"""Phase 2 Integration Architecture

## Current → Target flow

```
Upload (POST /api/files | /api/documents/upload)
  → UserFile + UploadJob(import) + OutboxEvent
  → worker._handle_import → _process_document (chunk/embed)
  → enqueue phase1_analysis          ← NEW (replaces extract_metadata+paper_analysis enqueue)
  → worker._handle_phase1_analysis
       → AnalysisPipelineService (1.1→1.7 black box)
       → persist analysis_pipeline_results
       → apply bibliographic metadata to UserFile
       → enqueue paper_analysis
  → worker._handle_paper_analysis
       → PromptBuilder.build(..., phase1_context=...)  ← consumes Phase 1
       → PaperAnalysis.data (LLM overview, backward compatible)

Sync path:
  POST /api/documents/<id>/analyze?sync=1  → AnalysisPipelineService inline
  POST /api/documents/<id>/analysis        → LLM analysis; injects phase1_context if persisted
  GET  /api/documents/<id>/pipeline        → full Phase 1 JSON
  GET  /api/documents/<id>/phases/<phase>  → one phase
```

## Correct Phase 1 order (repo truth)

1.1 Document Understanding → 1.2 Classification → 1.3 Analysis Context
→ 1.4 Medical Understanding → 1.5 Evidence Grading → 1.6 Prompt Assembly
→ 1.7 Knowledge Graph

(Plan's "1.4 Evidence Extraction / 1.5 Medical" labels were swapped vs this codebase.)

## Queue note

Postgres UploadJob worker (ADR-0001). No Celery/RQ introduced.

## Lazy migration

Existing documents keep working without a row. First analyze/worker pass creates
analysis_pipeline_results. Option A from the plan.

## Deprecated (kept, warned)

- worker extract_metadata handler (legacy in-flight jobs)
- server._apply_metadata / _run_paper_analysis thread paths
"""
