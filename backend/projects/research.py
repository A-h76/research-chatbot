"""ProjectResearchService — project-scoped cross-paper research (Sprint B).

Responsibilities only: resolve papers, validate ownership, assemble context,
build prompt (via PromptBuilder), run research, persist result.

Factory pattern: never ``import server``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from backend.projects.prompts import PRESET_TO_INTENT, VALID_PRESETS

# Analysis field names — valid ``section`` values when citing PaperAnalysis.
_ANALYSIS_SECTIONS = frozenset(
    {
        "executive_summary",
        "abstract_explained",
        "research_objective",
        "problem_statement",
        "methodology",
        "dataset",
        "experiments",
        "results",
        "key_contributions",
        "strengths",
        "limitations",
        "future_work",
        "keywords",
        "important_terms",
    }
)

# Phase 1 phase keys that may appear as section labels.
_PHASE1_SECTIONS = frozenset(
    {
        "classification",
        "analysis_context",
        "medical_understanding",
        "evidence_grading",
        "document_understanding",
        "prompt_assembly",
        "knowledge_graph",
    }
)

_VALID_SECTIONS = _ANALYSIS_SECTIONS | _PHASE1_SECTIONS

_MAX_PAPERS = 10
_MIN_PAPERS = 2
_MAX_PAPERS_JSON_CHARS = 18_000
_RECENT_RESEARCH_LIMIT = 20

_PRESET_LABELS = {
    "evidence": "Summarise the evidence",
    "disagree": "Where papers disagree",
    "methodology": "Compare methodologies",
    "open_questions": "Open questions",
    "compare": "Compare papers",
    "datasets": "Compare datasets",
}


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


def _selection_hash(
    file_ids: list[int],
    intent: str,
    query: str,
    analysis_versions: dict[int, str],
) -> str:
    """Stable cache key: papers + analysis versions + intent + query."""
    parts = [
        ",".join(str(i) for i in sorted(set(file_ids))),
        intent,
        (query or "").strip().lower(),
    ]
    for fid in sorted(analysis_versions):
        parts.append(f"{fid}:{analysis_versions[fid]}")
    key = "|".join(parts)
    return hashlib.sha256(key.encode()).hexdigest()


def _analysis_completeness(analysis: dict[str, Any]) -> int:
    score = 0
    for key in _ANALYSIS_SECTIONS:
        val = analysis.get(key)
        if val is None or val == "" or val == [] or val == {}:
            continue
        score += 1
    return score


def _first_author_citation(authors: str, year: str) -> str:
    first = (authors or "").split(";")[0].strip()
    if not first and not year:
        return ""
    if first and year:
        return f"{first} {year}"
    return first or year


@dataclass
class ProjectResearchService:
    SessionLocal: Callable[[], Any]
    select: Any
    Project: Any
    UserFile: Any
    PaperAnalysis: Any
    DerivedAnalysis: Any
    AnalysisPipelineResult: Any | None
    get_prompt_builder: Callable[[Any], Any]
    responses_text: Callable[..., str]
    utility_model: str
    build_phase1_prompt_context: Callable[[dict[str, Any], int], str] | None = None
    memory_promotion_service: Any | None = None
    _spawn_background: Callable[[Any, tuple], None] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._spawn_background is None:
            self._spawn_background = self._default_spawn_background

    @staticmethod
    def _default_spawn_background(target, args: tuple) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def _get_owned(self, db: Any, project_id: int, user_id: int) -> Any | None:
        p = db.get(self.Project, project_id)
        if not p or p.user_id != user_id:
            return None
        return p

    def _phase1_hint(self, db: Any, file_id: int) -> tuple[str, set[str]]:
        """Compact Phase 1 block + valid section names for this paper."""
        if self.AnalysisPipelineResult is None or not self.build_phase1_prompt_context:
            return "", set()
        try:
            row = db.execute(
                self.select(self.AnalysisPipelineResult).where(
                    self.AnalysisPipelineResult.file_id == file_id
                )
            ).scalar_one_or_none()
            if not row or not row.phase_results:
                return "", set()
            phases = json.loads(row.phase_results or "{}")
            if not isinstance(phases, dict):
                return "", set()
            hint = self.build_phase1_prompt_context(phases, max_chars=1500)
            valid = {k for k in phases if k in _PHASE1_SECTIONS}
            return hint, valid
        except Exception:
            return "", set()

    def _resolve_papers(
        self,
        db: Any,
        project_id: int,
        user_id: int,
        file_ids: list[int] | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, str]]:
        """Return (ready_blobs, skipped, analysis_versions)."""
        q = self.select(self.UserFile).where(
            self.UserFile.user_id == user_id,
            self.UserFile.project_id == project_id,
            self.UserFile.kind == "document",
        )
        if file_ids:
            q = q.where(self.UserFile.id.in_(file_ids))
        files = db.execute(q).scalars().all()
        file_by_id = {f.id: f for f in files}

        skipped: list[dict[str, Any]] = []
        if file_ids:
            for fid in file_ids:
                uf = file_by_id.get(fid)
                if not uf:
                    skipped.append({"id": fid, "reason": "not_in_project"})

        candidates: list[dict[str, Any]] = []
        analysis_versions: dict[int, str] = {}

        for uf in files:
            pa = db.execute(
                self.select(self.PaperAnalysis).where(self.PaperAnalysis.file_id == uf.id)
            ).scalar_one_or_none()
            if not pa or pa.status != "done":
                skipped.append(
                    {
                        "id": uf.id,
                        "name": uf.title or uf.name,
                        "reason": "analysis_not_ready",
                    }
                )
                continue

            analysis = {}
            try:
                analysis = json.loads(pa.data or "{}") if pa.data else {}
            except Exception:
                analysis = {}

            phase1_hint, phase1_sections = self._phase1_hint(db, uf.id)
            version = pa.content_hash or str(getattr(pa, "updated_at", "") or pa.id)
            analysis_versions[uf.id] = version

            candidates.append(
                {
                    "file_id": uf.id,
                    "title": uf.title or uf.name,
                    "authors": uf.authors or "",
                    "year": uf.year or "",
                    "citation": _first_author_citation(uf.authors or "", uf.year or ""),
                    "analysis": analysis,
                    "phase1_hint": phase1_hint,
                    "valid_sections": set(_ANALYSIS_SECTIONS) | phase1_sections,
                    "completeness": _analysis_completeness(analysis),
                    "updated_at": getattr(pa, "updated_at", None) or datetime.min.replace(tzinfo=timezone.utc),
                }
            )

        # Quality order: most complete → newest → id
        candidates.sort(
            key=lambda c: (c["completeness"], c["updated_at"], c["file_id"]),
            reverse=True,
        )
        candidates = candidates[:_MAX_PAPERS]

        # Token budget: pack highest-value papers first
        packed: list[dict[str, Any]] = []
        used = 0
        for c in candidates:
            blob = {
                "file_id": c["file_id"],
                "title": c["title"],
                "authors": c["authors"],
                "year": c["year"],
                "analysis": c["analysis"],
            }
            if c["phase1_hint"]:
                blob["phase1_sections"] = c["phase1_hint"]
            piece = json.dumps(blob, ensure_ascii=False)
            if packed and used + len(piece) > _MAX_PAPERS_JSON_CHARS:
                break
            packed.append({**c, "json_blob": blob})
            used += len(piece)

        return packed, skipped, analysis_versions

    def _normalize_claims(
        self,
        claims: Any,
        paper_meta: dict[int, dict[str, Any]],
        project_file_ids: set[int],
    ) -> tuple[list[dict[str, Any]], list[int], bool]:
        """Validate claims; strip invalid sections; enforce project scope."""
        if not isinstance(claims, list):
            return [], [], True

        out: list[dict[str, Any]] = []
        supporting: set[int] = set()
        incomplete = False

        for item in claims:
            if not isinstance(item, dict):
                incomplete = True
                continue
            claim_text = str(item.get("claim") or "").strip()
            if not claim_text:
                incomplete = True
                continue

            raw_support = item.get("support") or item.get("papers") or []
            if not isinstance(raw_support, list):
                incomplete = True
                continue

            support_out: list[dict[str, Any]] = []
            for s in raw_support:
                if not isinstance(s, dict):
                    continue
                try:
                    pid = int(s.get("paper_id") or s.get("file_id") or 0)
                except (TypeError, ValueError):
                    continue
                if pid not in project_file_ids or pid not in paper_meta:
                    incomplete = True
                    continue

                meta = paper_meta[pid]
                section = str(s.get("section") or "").strip()
                if section and section not in meta.get("valid_sections", _VALID_SECTIONS):
                    section = ""

                title = str(s.get("title") or meta.get("title") or "")
                snippet = str(s.get("snippet") or "").strip()
                citation = str(s.get("citation") or meta.get("citation") or "")

                support_out.append(
                    {
                        "paper_id": pid,
                        "title": title,
                        "section": section,
                        "snippet": snippet,
                        "citation": citation,
                    }
                )
                supporting.add(pid)

            if not support_out:
                incomplete = True
                continue

            out.append({"claim": claim_text, "support": support_out})

        if not out:
            incomplete = True
        return out, sorted(supporting), incomplete

    def _research_to_dict(self, da: Any, skipped: list | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if da.data:
            try:
                payload = json.loads(da.data)
            except Exception:
                payload = {}

        status = "running"
        if payload.get("error"):
            status = "failed"
        elif payload.get("answer") or payload.get("summary"):
            status = "done"
        elif da.data:
            status = "done"

        file_ids = []
        try:
            file_ids = json.loads(da.file_ids or "[]")
        except Exception:
            file_ids = []

        claims = payload.get("claims") or []
        supporting = payload.get("supporting_file_ids")
        if supporting is None:
            supporting = sorted(
                {
                    int(s.get("paper_id"))
                    for c in claims
                    if isinstance(c, dict)
                    for s in (c.get("support") or [])
                    if isinstance(s, dict) and s.get("paper_id") is not None
                }
            )

        return {
            "id": da.id,
            "kind": da.kind,
            "status": status,
            "preset": payload.get("preset"),
            "query": payload.get("query") or "",
            "file_ids": file_ids,
            "skipped": skipped or [],
            "summary": payload.get("summary") or "",
            "answer": payload.get("answer") or "",
            "claims": claims,
            "supporting_file_ids": supporting,
            "derived_analysis_id": da.id,
            "incomplete": bool(payload.get("incomplete")),
            "created_at": _iso(getattr(da, "created_at", None)),
        }

    def _run_background(
        self,
        derived_id: int,
        prompt: str,
        project_file_ids: set[int],
        paper_meta: dict[int, dict[str, Any]],
        request_meta: dict[str, str],
    ) -> None:
        db = self.SessionLocal()
        try:
            da = db.get(self.DerivedAnalysis, derived_id)
            if not da:
                return

            raw = self.responses_text(prompt, json_mode=True, kind="project_research", user_id=da.user_id)
            data = json.loads(raw)

            claims, supporting, incomplete = self._normalize_claims(
                data.get("claims"),
                paper_meta,
                project_file_ids,
            )

            result = {
                "summary": str(data.get("summary") or "")[:500],
                "answer": str(data.get("answer") or ""),
                "claims": claims,
                "supporting_file_ids": supporting,
                "preset": request_meta.get("preset") or "",
                "query": request_meta.get("query") or "",
                "intent": request_meta.get("intent") or "",
                "incomplete": incomplete,
            }

            da = db.get(self.DerivedAnalysis, derived_id)
            if not da:
                return
            da.data = json.dumps(result, ensure_ascii=False)
            da.model = self.utility_model
            db.commit()

            # Sprint C: promote only after successful persist
            if self.memory_promotion_service is not None and not result.get("error"):
                try:
                    self.memory_promotion_service.promote_research_result(
                        user_id=da.user_id,
                        project_id=da.project_id,
                        derived_id=derived_id,
                        result=result,
                    )
                except Exception as promo_exc:
                    logging.getLogger(__name__).warning(
                        "memory promotion after research failed derived_id=%s: %s",
                        derived_id,
                        promo_exc,
                    )
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "project research failed derived_id=%s: %s", derived_id, exc
            )
            try:
                da2 = db.get(self.DerivedAnalysis, derived_id)
                if da2:
                    da2.data = json.dumps({"error": str(exc), **request_meta})
                    da2.model = ""
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    def start_research(
        self,
        project_id: int,
        user_id: int,
        *,
        preset: str | None = None,
        query: str | None = None,
        file_ids: list[int] | None = None,
        force: bool = False,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Start or return cached research. Returns (payload, error_code)."""
        preset = (preset or "").strip() or None
        query = (query or "").strip()

        if preset and preset not in VALID_PRESETS:
            return None, "invalid_preset"

        if preset:
            intent = PRESET_TO_INTENT[preset]
        elif query:
            intent = "freeform"
            preset = None
        else:
            return None, "preset_or_query_required"

        db = self.SessionLocal()
        try:
            if self._get_owned(db, project_id, user_id) is None:
                return None, "not_found"

            requested_ids = [int(i) for i in (file_ids or []) if i]
            if requested_ids and len(requested_ids) > _MAX_PAPERS:
                return None, "too_many"

            packed, skipped, analysis_versions = self._resolve_papers(
                db, project_id, user_id, requested_ids or None
            )

            if len(packed) < _MIN_PAPERS:
                return None, "too_few_ready"

            valid_ids = [c["file_id"] for c in packed]
            project_file_ids = set(valid_ids)
            paper_meta = {c["file_id"]: c for c in packed}

            sel_hash = _selection_hash(valid_ids, intent, query, analysis_versions)

            existing = db.execute(
                self.select(self.DerivedAnalysis).where(
                    self.DerivedAnalysis.user_id == user_id,
                    self.DerivedAnalysis.project_id == project_id,
                    self.DerivedAnalysis.kind == "research",
                    self.DerivedAnalysis.selection_hash == sel_hash,
                )
            ).scalar_one_or_none()

            if existing and not force and existing.data:
                try:
                    payload = json.loads(existing.data)
                    if not payload.get("error"):
                        result = self._research_to_dict(existing, skipped)
                        return result, None
                except Exception:
                    pass

            papers_json = json.dumps([c["json_blob"] for c in packed], ensure_ascii=False, indent=1)

            builder = self.get_prompt_builder(db)
            # Light research-memory injection: pinned + contradictions + open questions only
            memory_context = ""
            try:
                memory_context = builder.build_project_memory_context(
                    user_id=user_id,
                    project_id=project_id,
                    light=True,
                    max_chars=2000,
                )
            except Exception:
                memory_context = ""

            prompt = builder.build_project_research(
                intent=intent,
                query=query,
                papers_json=papers_json[:_MAX_PAPERS_JSON_CHARS],
                memory_context=memory_context,
            )

            request_meta = {
                "preset": preset or "",
                "query": query,
                "intent": intent,
            }

            if existing and force:
                existing.data = ""
                existing.model = ""
                existing.file_ids = json.dumps(valid_ids)
                db.commit()
                da_id = existing.id
            elif existing and not existing.data:
                da_id = existing.id
            else:
                da = self.DerivedAnalysis(
                    user_id=user_id,
                    project_id=project_id,
                    kind="research",
                    selection_hash=sel_hash,
                    file_ids=json.dumps(valid_ids),
                )
                db.add(da)
                db.commit()
                da_id = da.id

            self._spawn_background(
                self._run_background,
                (da_id, prompt, project_file_ids, paper_meta, request_meta),
            )

            db.expire_all()
            da = db.get(self.DerivedAnalysis, da_id)
            result = self._research_to_dict(da, skipped)
            return result, None
        finally:
            db.close()

    def get_research(self, project_id: int, user_id: int, research_id: int) -> dict[str, Any] | None:
        db = self.SessionLocal()
        try:
            if self._get_owned(db, project_id, user_id) is None:
                return None
            da = db.get(self.DerivedAnalysis, research_id)
            if (
                not da
                or da.user_id != user_id
                or da.project_id != project_id
                or da.kind != "research"
            ):
                return None
            return self._research_to_dict(da)
        finally:
            db.close()

    def list_research(
        self,
        project_id: int,
        user_id: int,
        *,
        limit: int = _RECENT_RESEARCH_LIMIT,
    ) -> dict[str, Any] | None:
        """Recent research history for the project console."""
        db = self.SessionLocal()
        try:
            if self._get_owned(db, project_id, user_id) is None:
                return None
            rows = (
                db.execute(
                    self.select(self.DerivedAnalysis)
                    .where(
                        self.DerivedAnalysis.user_id == user_id,
                        self.DerivedAnalysis.project_id == project_id,
                        self.DerivedAnalysis.kind == "research",
                    )
                    .order_by(self.DerivedAnalysis.created_at.desc())
                    .limit(min(limit, _RECENT_RESEARCH_LIMIT))
                )
                .scalars()
                .all()
            )
            items = []
            for da in rows:
                d = self._research_to_dict(da)
                preset = d.get("preset") or ""
                label = _PRESET_LABELS.get(preset) or (d.get("query") or "Research")[:80]
                items.append(
                    {
                        "id": d["id"],
                        "status": d["status"],
                        "preset": preset,
                        "query": d.get("query") or "",
                        "label": label,
                        "summary": d.get("summary") or "",
                        "created_at": d.get("created_at"),
                    }
                )
            return {"items": items, "total": len(items)}
        finally:
            db.close()


def create_project_research_service(
    *,
    SessionLocal,
    select,
    Project,
    UserFile,
    PaperAnalysis,
    DerivedAnalysis,
    AnalysisPipelineResult=None,
    get_prompt_builder,
    responses_text,
    utility_model: str,
    build_phase1_prompt_context=None,
    memory_promotion_service=None,
) -> ProjectResearchService:
    return ProjectResearchService(
        SessionLocal=SessionLocal,
        select=select,
        Project=Project,
        UserFile=UserFile,
        PaperAnalysis=PaperAnalysis,
        DerivedAnalysis=DerivedAnalysis,
        AnalysisPipelineResult=AnalysisPipelineResult,
        get_prompt_builder=get_prompt_builder,
        responses_text=responses_text,
        utility_model=utility_model,
        build_phase1_prompt_context=build_phase1_prompt_context,
        memory_promotion_service=memory_promotion_service,
    )
