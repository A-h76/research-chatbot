"""Persistence → pure-dict adapters for ``RetrievedBundle``.

Adapters translate only. No ranking, prompting, orchestration, or ORM.
Callers that talk to SQLAlchemy must convert rows to dicts *before*
passing data here (or use a ``Phase1Source`` that does so at the edge).
"""

from backend.ai_core.adapters.citations import adapt_citations
from backend.ai_core.adapters.notes import adapt_notes
from backend.ai_core.adapters.phase1 import adapt_phase1
from backend.ai_core.adapters.project import adapt_project

__all__ = [
    "adapt_citations",
    "adapt_notes",
    "adapt_phase1",
    "adapt_project",
]
