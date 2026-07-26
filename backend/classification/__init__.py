"""Classification package — multi-pass document understanding. Each pass
is its own sub-package, so a new pass is a new sub-package, not a change
to an existing one:

- pass1: domain/document-type/publication-type, built on
  backend.processing's ProcessedDocument (Phase 1's flat, string-keyed
  document model).
- pass2: document_type/domain/study_design/reporting_guideline, built on
  backend.document_understanding's ProcessedDocument (Phase 1.1's
  composed, enum-keyed document model) — a richer label set and a
  different consumer, not a replacement for pass1. Reuses pass1.rules'
  generic scoring engine directly rather than duplicating it.

Later passes are future work.
"""
