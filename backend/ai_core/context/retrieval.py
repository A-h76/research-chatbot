"""Retrieve Phase 1 / notes / citations / passages into a pure ``RetrievedBundle``.

Sprint 3: no DB/ORM wiring. Returns an empty bundle so the builder pipeline
runs end-to-end. Later sprints fill this without leaking SQLAlchemy models
into ``ResearchContext``.
"""

from __future__ import annotations

from backend.ai_core.context.bundle import RetrievedBundle


class ContextRetrieval:
    """Fetch raw material for a file/project scope — ORM stays inside this class later."""

    def retrieve(
        self,
        *,
        file_id: int | None = None,
        project_id: int | None = None,
        question: str | None = None,
        **_: object,
    ) -> RetrievedBundle:
        """Return a pure bundle. Empty until Phase 1 adapters land."""
        return RetrievedBundle(
            meta={
                "file_id": file_id,
                "project_id": project_id,
                "question": question,
                "source": "empty_stub",
            },
        )


# Module-level helpers kept for explicit low-level use / tests.

def retrieve_phase_bundle(file_id: int) -> dict:
    """Legacy stub name — prefer ``ContextRetrieval.retrieve``."""
    bundle = ContextRetrieval().retrieve(file_id=file_id)
    return {
        "document": bundle.document,
        "classification": bundle.classification,
        "entities": bundle.entities,
        "evidence": bundle.evidence,
        "graph": bundle.graph,
        "narrative": bundle.narrative,
    }


def retrieve_notes(*, file_id: int | None = None, project_id: int | None = None) -> list[dict]:
    return list(ContextRetrieval().retrieve(file_id=file_id, project_id=project_id).notes)


def retrieve_citations(
    *,
    file_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    return list(ContextRetrieval().retrieve(file_id=file_id, project_id=project_id).citations)
