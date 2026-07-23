"""MemoryEngine — relevance filtering over the existing Memory model
(server.py's `memories` table) for prompt assembly (Prompt Builder's
"Memory" layer — docs/prompt-engine-architecture.md §7). No new table:
Memory already has everything this needs (user_id, project_id, fact,
importance, created_at) — this is a query/ranking class, not a storage
layer.

Constructor-injected (db_session, Memory) — same reason as everything
else in backend/ai: never `import server`; Memory comes from whichever
Base actually owns it (server.py's own), not redeclared here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    # Static-analysis only — never executed, so this doesn't violate the
    # "never import server at runtime" rule (see module docstring): the
    # import is erased entirely before Python runs the module.
    from server import Memory


class MemoryEngine:
    def __init__(self, db_session, Memory):
        self.db = db_session
        self.Memory = Memory

    def get_relevant_memories(
        self,
        user_id: int,
        query: str,
        project_id: Optional[int] = None,
        limit: int = 5,
    ) -> List[Memory]:
        """Project-scoping matches server.py's own build_system_prompt()
        exactly (global_mems + proj_mems), not a new convention invented
        here: project_id=None -> global memories only (project_id IS
        NULL); project_id=<id> -> that project's memories *plus* global
        ones, never other projects'."""
        M = self.Memory
        q = self.db.query(M).filter(M.user_id == user_id)
        if project_id is not None:
            q = q.filter((M.project_id.is_(None)) | (M.project_id == project_id))
        else:
            q = q.filter(M.project_id.is_(None))
        candidates = q.all()

        terms = {t.lower() for t in query.split() if len(t) > 2}

        def keyword_hits(m):
            fact_words = m.fact.lower().split()
            return sum(1 for t in terms if any(t in w for w in fact_words))

        # TODO: naive token-overlap relevance, no embeddings — fine at the
        # memory-per-user volumes this app has today. If a user's memory
        # count grows past roughly 100, upgrade to a stored embedding +
        # cosine rank (same pattern backend/search/routes.py already uses
        # for Chunk) — plain token overlap gets noisy and stops
        # meaningfully discriminating well before it gets slow.
        ranked = sorted(
            candidates,
            key=lambda m: (keyword_hits(m), m.importance, m.created_at),
            reverse=True,
        )
        return ranked[:limit]
