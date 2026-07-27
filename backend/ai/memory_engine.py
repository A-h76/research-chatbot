"""MemoryEngine — relevance filtering over the existing Memory model
(server.py's `memories` table) for prompt assembly (Prompt Builder's
"Memory" layer — docs/prompt-engine-architecture.md §7). No new table:
Memory already has everything this needs (user_id, project_id, fact,
importance, created_at) — this is a query/ranking class, not a storage
layer.

Sprint C adds get_project_memory_context() for research memory injection.
Chat-derived memories (source='chat') are excluded from research context.

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

# Research context never includes chat-extracted rows.
_RESEARCH_SOURCES = frozenset({"research", "manual", "compare", "gaps"})

_KIND_PRIORITY = {
    "contradiction": 5,
    "open_question": 4,
    "finding": 3,
    "claim": 2,
    "insight": 1,
    "fact": 0,
}


class MemoryEngine:
    def __init__(self, db_session, Memory):
        self.db = db_session
        self.Memory = Memory

    def get_chat_memories(
        self, user_id: int, project_id: Optional[int] = None
    ) -> tuple[list[str], list[str]]:
        """All memories for chat parity with server.build_system_prompt().

        Returns (global_facts, project_facts). Unlike get_relevant_memories(),
        this does not rank or truncate — Phase A chat migration requires
        identical behavior to the legacy assembler.

        Project facts here are chat/legacy only when research injection is
        handled separately via get_project_memory_context (see PromptBuilder).
        """
        M = self.Memory
        global_q = self.db.query(M).filter(M.user_id == user_id, M.project_id.is_(None))
        if hasattr(M, "status"):
            global_q = global_q.filter((M.status.is_(None)) | (M.status == "active") | (M.status == ""))
        global_mems = [m.fact for m in global_q.all()]

        proj_mems: list[str] = []
        if project_id is not None:
            # Legacy dump kept for callers that don't use research context;
            # prefer get_project_memory_context for project chat injection.
            pq = self.db.query(M).filter(M.user_id == user_id, M.project_id == project_id)
            if hasattr(M, "status"):
                pq = pq.filter((M.status.is_(None)) | (M.status == "active") | (M.status == ""))
            proj_mems = [m.fact for m in pq.all()]
        return global_mems, proj_mems

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
        if hasattr(M, "status"):
            q = q.filter((M.status.is_(None)) | (M.status == "active") | (M.status == ""))
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

    def get_project_memory_context(
        self,
        user_id: int,
        project_id: int,
        *,
        kinds: Optional[list[str]] = None,
        max_chars: int = 4000,
        light: bool = False,
    ) -> list[Memory]:
        """Highest-value project research memories for prompt injection.

        Ranking (frozen Sprint C): pinned → kind priority → importance → created_at DESC.
        Excludes source='chat'. Soft-deleted / archived excluded.

        light=True (research console): only pinned + contradiction + open_question.
        """
        M = self.Memory
        if not hasattr(M, "source"):
            return []

        q = self.db.query(M).filter(
            M.user_id == user_id,
            M.project_id == project_id,
            M.status == "active",
            M.source.in_(tuple(_RESEARCH_SOURCES)),
        )
        if light:
            q = q.filter(
                (M.pinned == 1)
                | (M.kind.in_(("contradiction", "open_question")))
            )
        if kinds:
            q = q.filter(M.kind.in_(tuple(kinds)))

        candidates = q.all()
        ranked = sorted(
            candidates,
            key=lambda m: (
                1 if getattr(m, "pinned", 0) else 0,
                _KIND_PRIORITY.get(getattr(m, "kind", "") or "fact", 0),
                int(m.importance or 0),
                m.created_at or 0,
            ),
            reverse=True,
        )

        out: list[Memory] = []
        used = 0
        for m in ranked:
            piece = (m.fact or "").strip()
            if not piece:
                continue
            cost = len(piece) + 8
            if out and used + cost > max_chars:
                break
            out.append(m)
            used += cost
        return out
