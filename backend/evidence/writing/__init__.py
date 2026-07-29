"""Writing Intelligence internal modules (v0.2.1 Lit Review vertical).

Planner → Context Builder → Section Generator → Citation Binder → Reviewer → metrics.
Public stage entry remains backend.evidence.writing_intelligence.
"""

from .citation_binder import bind_citations_to_sections, flatten_bindings
from .context_builder import build_section_contexts, build_structured_argument
from .export_markdown import build_literature_review_markdown, compute_export_traceability
from .metrics import compute_writing_metrics
from .planner import SECTION_TYPES, plan_sections
from .reviewer import review_grounded_draft
from .section_generator import generate_sections

__all__ = [
    "SECTION_TYPES",
    "plan_sections",
    "build_section_contexts",
    "build_structured_argument",
    "generate_sections",
    "bind_citations_to_sections",
    "flatten_bindings",
    "review_grounded_draft",
    "compute_writing_metrics",
    "build_literature_review_markdown",
    "compute_export_traceability",
]
