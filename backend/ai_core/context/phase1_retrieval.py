"""Phase-1-backed ``ContextRetrieval`` — composition of adapters only.

Knows how to ask a ``Phase1Source`` for persistence-shaped data, then
translates via adapters into a pure ``RetrievedBundle``. Ranking /
compression stay outside this class.
"""

from __future__ import annotations

from typing import Any, Protocol

from backend.ai_core.adapters.citations import adapt_citations
from backend.ai_core.adapters.notes import adapt_notes
from backend.ai_core.adapters.phase1 import adapt_phase1
from backend.ai_core.adapters.project import adapt_project
from backend.ai_core.context.bundle import RetrievedBundle
from backend.ai_core.context.retrieval import ContextRetrieval


class Phase1Source(Protocol):
    """Persistence edge — returns JSON-friendly dicts only (no ORM objects)."""

    def get_phase_results(self, file_id: int) -> dict[str, Any] | None: ...

    def get_notes(
        self,
        *,
        file_id: int | None = None,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_citations(
        self,
        *,
        file_id: int | None = None,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_project(self, project_id: int) -> dict[str, Any] | None: ...


class MemoryPhase1Source:
    """In-memory source for tests and local fixtures (no database)."""

    def __init__(
        self,
        *,
        phase_results_by_file: dict[int, dict[str, Any]] | None = None,
        notes: list[dict[str, Any]] | None = None,
        citations: list[dict[str, Any]] | None = None,
        projects: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self._phases = phase_results_by_file or {}
        self._notes = notes or []
        self._citations = citations or []
        self._projects = projects or {}

    def get_phase_results(self, file_id: int) -> dict[str, Any] | None:
        return self._phases.get(file_id)

    def get_notes(
        self,
        *,
        file_id: int | None = None,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if file_id is None and project_id is None:
            return list(self._notes)
        out: list[dict[str, Any]] = []
        for n in self._notes:
            if file_id is not None and n.get("file_id") == file_id:
                out.append(n)
            elif project_id is not None and n.get("project_id") == project_id:
                out.append(n)
        return out

    def get_citations(
        self,
        *,
        file_id: int | None = None,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if project_id is None and file_id is None:
            return list(self._citations)
        out: list[dict[str, Any]] = []
        for c in self._citations:
            if project_id is not None and c.get("project_id") == project_id:
                out.append(c)
            elif file_id is not None and c.get("file_id") == file_id:
                out.append(c)
        return out

    def get_project(self, project_id: int) -> dict[str, Any] | None:
        return self._projects.get(project_id)


class Phase1Retrieval(ContextRetrieval):
    """Real retrieval path: source → adapters → ``RetrievedBundle``."""

    def __init__(self, source: Phase1Source) -> None:
        self._source = source

    def retrieve(
        self,
        *,
        file_id: int | None = None,
        project_id: int | None = None,
        question: str | None = None,
        **_: object,
    ) -> RetrievedBundle:
        phases: dict[str, Any] = {}
        if file_id is not None:
            loaded = self._source.get_phase_results(file_id)
            if loaded:
                phases = loaded

        bundle = adapt_phase1(phases)
        notes = adapt_notes(
            self._source.get_notes(file_id=file_id, project_id=project_id)
        )
        citations = adapt_citations(
            self._source.get_citations(file_id=file_id, project_id=project_id)
        )
        project: dict[str, Any] = {}
        if project_id is not None:
            project = adapt_project(self._source.get_project(project_id))

        bundle.notes = notes
        bundle.citations = citations
        bundle.meta = {
            **bundle.meta,
            "file_id": file_id,
            "project_id": project_id,
            "question": question,
            "source": "phase1_retrieval",
            "project": project,
            "has_phase1": bool(phases),
        }
        return bundle
