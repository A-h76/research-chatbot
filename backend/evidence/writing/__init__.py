"""Writing Intelligence internal modules (v0.2.1 Lit Review vertical).

Planner → Context Builder → Section Generator → Citation Binder → Reviewer → metrics.
Public stage entry remains backend.evidence.writing_intelligence.
"""

from .citation_binder import bind_citations_to_sections, flatten_bindings
from .context_builder import build_section_contexts, build_structured_argument
from .export_markdown import (
    build_bibtex_from_writing,
    build_literature_review_markdown,
    can_export_grounded_lit_review,
    compute_export_traceability,
    merge_persisted_review_into_writing,
)
from .metrics import compute_writing_metrics
from .planner import SECTION_TYPES, plan_sections
from .reviewer import review_grounded_draft
from .reviewer_engine import execute_reviewer
from .ri_depth import (
    build_draft_metadata,
    build_ri_writing_context,
    build_theme_outline,
    merge_ri_into_argument,
)
from .section_generator import generate_sections

__all__ = [
    "SECTION_TYPES",
    "plan_sections",
    "build_section_contexts",
    "build_structured_argument",
    "build_ri_writing_context",
    "build_theme_outline",
    "build_draft_metadata",
    "merge_ri_into_argument",
    "generate_sections",
    "bind_citations_to_sections",
    "flatten_bindings",
    "review_grounded_draft",
    "execute_reviewer",
    "compute_writing_metrics",
    "build_literature_review_markdown",
    "build_bibtex_from_writing",
    "can_export_grounded_lit_review",
    "compute_export_traceability",
    "merge_persisted_review_into_writing",
]
