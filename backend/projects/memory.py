"""MemoryPromotionService — promote Sprint B research into project memories.

Responsibilities only: extract, classify, dedupe (upsert), save, pin/archive,
list. No routes, no prompt building, no chat.

Guiding rule: Research Memory is produced from research outputs, not conversations.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

_MEMORY_KINDS = frozenset(
    {"finding", "claim", "contradiction", "open_question", "insight", "fact"}
)
_MEMORY_SOURCES = frozenset({"research", "compare", "gaps", "manual", "chat"})
_MEMORY_STATUSES = frozenset({"active", "archived", "deleted"})

# Research-context sources only (chat excluded — product identity).
RESEARCH_CONTEXT_SOURCES = frozenset({"research", "manual", "compare", "gaps"})

_KIND_PRIORITY = {
    "contradiction": 5,
    "open_question": 4,
    "finding": 3,
    "claim": 2,
    "insight": 1,
    "fact": 0,
}

_MAX_CLAIMS_PER_RUN = 8
_FACT_MAX = 1000

_OPEN_Q_RE = re.compile(
    r"\b(future work|unanswered|remain(?:s|ing)?\s+(?:open|unclear)|open question|limitation)\b",
    re.I,
)
_DISAGREE_RE = re.compile(
    r"\b(disagree|contradict|conflict|tension|diverge|inconsisten)\w*\b",
    re.I,
)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


def normalize_claim_text(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t


def claim_hash_for(text: str) -> str:
    return hashlib.sha256(normalize_claim_text(text).encode()).hexdigest()


def _classify_claim(*, preset: str, claim_text: str) -> str:
    """Structured preset first; text heuristics only enrich."""
    if preset == "disagree":
        return "contradiction"
    if preset == "open_questions":
        return "open_question"
    if _DISAGREE_RE.search(claim_text):
        return "contradiction"
    if _OPEN_Q_RE.search(claim_text):
        return "open_question"
    return "claim"


@dataclass
class MemoryPromotionService:
    SessionLocal: Callable[[], Any]
    select: Any
    Project: Any
    UserFile: Any
    Memory: Any
    DerivedAnalysis: Any

    def _owned_project(self, db: Any, project_id: int, user_id: int) -> Any | None:
        p = db.get(self.Project, project_id)
        if not p or p.user_id != user_id:
            return None
        return p

    def _project_file_ids(self, db: Any, project_id: int, user_id: int) -> set[int]:
        rows = (
            db.execute(
                self.select(self.UserFile.id).where(
                    self.UserFile.user_id == user_id,
                    self.UserFile.project_id == project_id,
                    self.UserFile.kind == "document",
                )
            )
            .scalars()
            .all()
        )
        return set(int(i) for i in rows)

    def _validate_paper_ids(
        self, paper_ids: list[int], project_file_ids: set[int]
    ) -> list[int]:
        return [int(i) for i in paper_ids if int(i) in project_file_ids]

    def serialize(self, m: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        try:
            payload = json.loads(m.payload or "{}") if getattr(m, "payload", None) else {}
        except Exception:
            payload = {}
        return {
            "id": m.id,
            "project_id": m.project_id,
            "fact": m.fact,
            "kind": getattr(m, "kind", None) or "fact",
            "source": getattr(m, "source", None) or "chat",
            "source_ref": getattr(m, "source_ref", None) or "",
            "payload": payload,
            "pinned": bool(getattr(m, "pinned", 0)),
            "status": getattr(m, "status", None) or "active",
            "importance": m.importance if m.importance is not None else 3,
            "claim_hash": getattr(m, "claim_hash", None) or "",
            "created_at": _iso(getattr(m, "created_at", None)),
        }

    def _upsert(
        self,
        db: Any,
        *,
        user_id: int,
        project_id: int,
        kind: str,
        source: str,
        source_ref: str,
        fact: str,
        payload: dict[str, Any],
        importance: int = 3,
    ) -> Any:
        ch = claim_hash_for(fact)
        existing = db.execute(
            self.select(self.Memory).where(
                self.Memory.user_id == user_id,
                self.Memory.project_id == project_id,
                self.Memory.kind == kind,
                self.Memory.claim_hash == ch,
                self.Memory.status != "deleted",
            )
        ).scalar_one_or_none()

        if existing:
            existing.fact = fact[:_FACT_MAX]
            existing.source = source
            existing.source_ref = source_ref
            existing.payload = json.dumps(payload, ensure_ascii=False)
            existing.importance = max(int(existing.importance or 3), importance)
            if getattr(existing, "status", "active") == "archived":
                pass  # keep archived; still refresh content
            return existing

        row = self.Memory(
            user_id=user_id,
            project_id=project_id,
            fact=fact[:_FACT_MAX],
            importance=importance,
            kind=kind,
            source=source,
            source_ref=source_ref,
            payload=json.dumps(payload, ensure_ascii=False),
            pinned=0,
            status="active",
            claim_hash=ch,
        )
        db.add(row)
        return row

    def promote_research_result(
        self,
        *,
        user_id: int,
        project_id: int,
        derived_id: int,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Idempotent upsert from a completed research result. Returns counts."""
        db = self.SessionLocal()
        created = updated = 0
        try:
            if self._owned_project(db, project_id, user_id) is None:
                return {"error": "not_found", "created": 0, "updated": 0}

            da = db.get(self.DerivedAnalysis, derived_id)
            if (
                not da
                or da.user_id != user_id
                or da.project_id != project_id
                or da.kind != "research"
            ):
                return {"error": "invalid_source_ref", "created": 0, "updated": 0}

            project_files = self._project_file_ids(db, project_id, user_id)
            source_ref = f"derived_analysis:{derived_id}"
            preset = str(result.get("preset") or "")
            before_ids = {
                m.id
                for m in db.execute(
                    self.select(self.Memory).where(
                        self.Memory.user_id == user_id,
                        self.Memory.project_id == project_id,
                        self.Memory.source_ref == source_ref,
                        self.Memory.status != "deleted",
                    )
                )
                .scalars()
                .all()
            }

            summary = str(result.get("summary") or "").strip()
            if summary:
                paper_ids = self._validate_paper_ids(
                    list(result.get("supporting_file_ids") or []),
                    project_files,
                )
                self._upsert(
                    db,
                    user_id=user_id,
                    project_id=project_id,
                    kind="finding",
                    source="research",
                    source_ref=source_ref,
                    fact=summary,
                    payload={"paper_ids": paper_ids, "claim": summary, "citations": []},
                    importance=4,
                )

            claims = result.get("claims") or []
            if not isinstance(claims, list):
                claims = []
            for item in claims[:_MAX_CLAIMS_PER_RUN]:
                if not isinstance(item, dict):
                    continue
                claim_text = str(item.get("claim") or "").strip()
                if not claim_text:
                    continue
                kind = _classify_claim(preset=preset, claim_text=claim_text)
                support = item.get("support") or []
                paper_ids: list[int] = []
                citations: list[dict[str, Any]] = []
                if isinstance(support, list):
                    for s in support:
                        if not isinstance(s, dict):
                            continue
                        try:
                            pid = int(s.get("paper_id") or 0)
                        except (TypeError, ValueError):
                            continue
                        if pid in project_files:
                            paper_ids.append(pid)
                            citations.append(
                                {
                                    "paper_id": pid,
                                    "title": s.get("title") or "",
                                    "section": s.get("section") or "",
                                    "snippet": s.get("snippet") or "",
                                    "citation": s.get("citation") or "",
                                }
                            )
                paper_ids = sorted(set(paper_ids))
                self._upsert(
                    db,
                    user_id=user_id,
                    project_id=project_id,
                    kind=kind,
                    source="research",
                    source_ref=source_ref,
                    fact=claim_text,
                    payload={
                        "paper_ids": paper_ids,
                        "claim": claim_text,
                        "citations": citations,
                    },
                    importance=4 if kind in ("contradiction", "open_question") else 3,
                )

            db.commit()

            after = (
                db.execute(
                    self.select(self.Memory).where(
                        self.Memory.user_id == user_id,
                        self.Memory.project_id == project_id,
                        self.Memory.source_ref == source_ref,
                        self.Memory.status != "deleted",
                    )
                )
                .scalars()
                .all()
            )
            after_ids = {m.id for m in after}
            created = len(after_ids - before_ids)
            updated = len(after_ids & before_ids)
            return {"created": created, "updated": updated, "total": len(after_ids)}
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "memory promotion failed derived_id=%s: %s", derived_id, exc
            )
            db.rollback()
            return {"error": str(exc), "created": 0, "updated": 0}
        finally:
            db.close()

    def list_memories(
        self,
        project_id: int,
        user_id: int,
        *,
        kind: str | None = None,
        source: str | None = None,
        pinned: bool | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any] | None:
        db = self.SessionLocal()
        try:
            if self._owned_project(db, project_id, user_id) is None:
                return None
            q = self.select(self.Memory).where(
                self.Memory.user_id == user_id,
                self.Memory.project_id == project_id,
                self.Memory.status != "deleted",
            )
            if not include_archived:
                q = q.where(self.Memory.status == "active")
            else:
                q = q.where(self.Memory.status.in_(("active", "archived")))
            if kind:
                q = q.where(self.Memory.kind == kind)
            if source:
                q = q.where(self.Memory.source == source)
            if pinned is not None:
                q = q.where(self.Memory.pinned == (1 if pinned else 0))
            rows = (
                db.execute(q.order_by(self.Memory.pinned.desc(), self.Memory.created_at.desc()))
                .scalars()
                .all()
            )
            items = [self.serialize(m) for m in rows]
            return {"items": items, "total": len(items)}
        finally:
            db.close()

    def update_memory(
        self,
        project_id: int,
        memory_id: int,
        user_id: int,
        *,
        action: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """pin|unpin|archive|restore. AI-generated fact text is immutable."""
        action = (action or "").strip().lower()
        if action not in ("pin", "unpin", "archive", "restore"):
            return None, "invalid_action"

        db = self.SessionLocal()
        try:
            if self._owned_project(db, project_id, user_id) is None:
                return None, "not_found"
            m = db.get(self.Memory, memory_id)
            if not m or m.user_id != user_id or m.project_id != project_id:
                return None, "not_found"
            if (getattr(m, "status", None) or "active") == "deleted":
                return None, "not_found"

            if action == "pin":
                m.pinned = 1
            elif action == "unpin":
                m.pinned = 0
            elif action == "archive":
                m.status = "archived"
                m.pinned = 0
            elif action == "restore":
                m.status = "active"

            db.commit()
            db.refresh(m)
            return self.serialize(m), None
        finally:
            db.close()

    def soft_delete(
        self, project_id: int, memory_id: int, user_id: int
    ) -> str | None:
        db = self.SessionLocal()
        try:
            if self._owned_project(db, project_id, user_id) is None:
                return "not_found"
            m = db.get(self.Memory, memory_id)
            if not m or m.user_id != user_id or m.project_id != project_id:
                return "not_found"
            m.status = "deleted"
            m.pinned = 0
            db.commit()
            return None
        finally:
            db.close()


def create_memory_promotion_service(
    *,
    SessionLocal,
    select,
    Project,
    UserFile,
    Memory,
    DerivedAnalysis,
) -> MemoryPromotionService:
    return MemoryPromotionService(
        SessionLocal=SessionLocal,
        select=select,
        Project=Project,
        UserFile=UserFile,
        Memory=Memory,
        DerivedAnalysis=DerivedAnalysis,
    )
