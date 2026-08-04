"""AnalysisPipelineService — single entry for all document analysis."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Optional

from backend.analysis_context.pipeline import AnalysisContextPipeline
from backend.classification.pass2.pipeline import DocumentClassificationPipeline
from backend.document_understanding.pipeline import DocumentUnderstandingPipeline
from backend.evidence_grading.pipeline import EvidenceGradingPipeline
from backend.knowledge_graph.pipeline import KnowledgeGraphPipeline
from backend.medical_understanding.pipeline import MedicalUnderstandingPipeline
from backend.prompt_assembly.pipeline import PromptAssemblyPipeline

from .models import AnalysisJobStatus, AnalysisOptions, AnalysisResult
from .serialize import to_jsonable

log = logging.getLogger(__name__)

PIPELINE_VERSION = "2.0.0"  # integration layer version (not Phase 1 package versions)


class AnalysisPipelineService:
    """Runs Phase 1.1–1.7 in order. Phase 1 packages are used as black boxes."""

    def __init__(self) -> None:
        self.document_understanding = DocumentUnderstandingPipeline()
        self.classification = DocumentClassificationPipeline()
        self.analysis_context = AnalysisContextPipeline()
        self.medical_understanding = MedicalUnderstandingPipeline()
        self.evidence_grading = EvidenceGradingPipeline()
        self.prompt_assembly = PromptAssemblyPipeline()
        self.knowledge_graph = KnowledgeGraphPipeline()

    def analyze_file_path(
        self,
        path: str | Path,
        *,
        file_id: int,
        options: Optional[AnalysisOptions] = None,
        document_id: Optional[str] = None,
    ) -> AnalysisResult:
        options = options or AnalysisOptions()
        warnings: list[str] = []
        errors: list[str] = []
        phases: dict[str, Any] = {}
        start = time.perf_counter()
        path = Path(path)

        # 1.1
        try:
            document = self.document_understanding.process(
                path,
                metadata={"id": document_id or str(file_id)},
            )
        except Exception as exc:
            log.exception("Phase 1.1 failed for file_id=%s", file_id)
            return AnalysisResult(
                file_id=file_id,
                content_hash="",
                status=AnalysisJobStatus.FAILED,
                errors=[f"document_understanding: {exc}"],
                pipeline_version=PIPELINE_VERSION,
                total_processing_time_ms=(time.perf_counter() - start) * 1000,
            )

        content_hash = _hash_text(getattr(document, "full_text", None) or getattr(document, "text", "") or "")
        phases["document_understanding"] = _serialize_document(document, options)

        classification = None
        context = None
        medical = None
        grades = None
        prompt = None
        graph = None

        # 1.2
        if options.run_classification:
            classification, w, e = _run_phase(
                "classification",
                lambda: self.classification.process(document),
            )
            warnings.extend(w)
            errors.extend(e)
            if classification is not None:
                phases["classification"] = to_jsonable(classification)

        # Paper Analysis 2.2 — methodology profile (DU + classification; medical later).
        _attach_methodology_profile(phases)
        # Paper Analysis 2.3 — statistical findings (DU; medical enrich later).
        _attach_statistics_profile(phases)
        # Paper Analysis 2.5 — author-stated limitations / novelty.
        _attach_limitations_novelty_profile(phases)
        # Paper Analysis 2.6 — paper-scoped scientific entities (from profiles).
        _attach_scientific_entities_profile(phases)
        # Paper Analysis 2.7 — inspectable quality checklist (aggregate profiles).
        _attach_quality_assessment_profile(phases)

        # 1.3
        if options.run_analysis_context and classification is not None:
            context, w, e = _run_phase(
                "analysis_context",
                lambda: self.analysis_context.process(document, classification),
            )
            warnings.extend(w)
            errors.extend(e)
            if context is not None:
                phases["analysis_context"] = to_jsonable(context)

        # 1.4
        if options.run_medical and classification is not None and context is not None:
            medical, w, e = _run_phase(
                "medical_understanding",
                lambda: self.medical_understanding.process(document, classification, context),
            )
            warnings.extend(w)
            errors.extend(e)
            if medical is not None:
                phases["medical_understanding"] = to_jsonable(medical)
                # Re-attach with PICO / medical enrichment when medical phase succeeded.
                _attach_methodology_profile(phases)
                _attach_statistics_profile(phases)
                _attach_scientific_entities_profile(phases)
                _attach_quality_assessment_profile(phases)

        # 1.5
        if (
            options.run_evidence_grading
            and classification is not None
            and context is not None
            and medical is not None
        ):
            grades, w, e = _run_phase(
                "evidence_grading",
                lambda: self.evidence_grading.process(document, classification, context, medical),
            )
            warnings.extend(w)
            errors.extend(e)
            if grades is not None:
                phases["evidence_grading"] = to_jsonable(grades)

        # 1.6
        if (
            options.run_prompt_assembly
            and classification is not None
            and context is not None
            and medical is not None
            and grades is not None
        ):
            prompt, w, e = _run_phase(
                "prompt_assembly",
                lambda: self.prompt_assembly.process(
                    document, classification, context, medical, grades
                ),
            )
            warnings.extend(w)
            errors.extend(e)
            if prompt is not None:
                phases["prompt_assembly"] = to_jsonable(prompt, max_str=options.max_full_text_chars)

        # 1.7
        if (
            options.run_knowledge_graph
            and classification is not None
            and context is not None
            and medical is not None
            and grades is not None
            and prompt is not None
        ):
            graph, w, e = _run_phase(
                "knowledge_graph",
                lambda: self.knowledge_graph.process(
                    document, classification, context, medical, grades, prompt
                ),
            )
            warnings.extend(w)
            errors.extend(e)
            if graph is not None:
                payload = to_jsonable(graph)
                if not options.persist_graph_formats and isinstance(payload, dict):
                    payload.pop("formats", None)
                phases["knowledge_graph"] = payload

        status = AnalysisJobStatus.DONE
        if errors and len(phases) <= 1:
            status = AnalysisJobStatus.FAILED
        elif errors:
            status = AnalysisJobStatus.PARTIAL

        return AnalysisResult(
            file_id=file_id,
            content_hash=content_hash,
            status=status,
            phase_results=phases,
            pipeline_version=PIPELINE_VERSION,
            total_processing_time_ms=(time.perf_counter() - start) * 1000,
            warnings=warnings,
            errors=errors,
        )


def _run_phase(name: str, fn):
    warnings: list[str] = []
    errors: list[str] = []
    try:
        return fn(), warnings, errors
    except Exception as exc:  # noqa: BLE001 — isolate phase failures
        log.exception("Phase %s failed", name)
        errors.append(f"{name}: {exc}")
        return None, warnings, errors


def _attach_methodology_profile(phases: dict[str, Any]) -> None:
    """Additive methodology_profile on document_understanding (2.2)."""
    du = phases.get("document_understanding")
    if not isinstance(du, dict):
        return
    try:
        from backend.document_understanding.methodology_profile import (
            extract_methodology_profile,
        )

        clf = phases.get("classification") if isinstance(phases.get("classification"), dict) else None
        med = (
            phases.get("medical_understanding")
            if isinstance(phases.get("medical_understanding"), dict)
            else None
        )
        du["methodology_profile"] = extract_methodology_profile(
            du, classification=clf, medical=med
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("methodology_profile extract skipped: %s", exc)
        du["methodology_profile"] = {
            "schema_version": "1.0.0",
            "has_content": False,
            "error": str(exc),
        }


def _attach_statistics_profile(phases: dict[str, Any]) -> None:
    """Additive statistics_profile on document_understanding (2.3)."""
    du = phases.get("document_understanding")
    if not isinstance(du, dict):
        return
    try:
        from backend.document_understanding.statistics_profile import (
            extract_statistics_profile,
        )

        med = (
            phases.get("medical_understanding")
            if isinstance(phases.get("medical_understanding"), dict)
            else None
        )
        du["statistics_profile"] = extract_statistics_profile(du, medical=med)
    except Exception as exc:  # noqa: BLE001
        log.warning("statistics_profile extract skipped: %s", exc)
        du["statistics_profile"] = {
            "schema_version": "1.0.0",
            "has_content": False,
            "error": str(exc),
        }


def _attach_limitations_novelty_profile(phases: dict[str, Any]) -> None:
    """Additive limitations_novelty_profile on document_understanding (2.5)."""
    du = phases.get("document_understanding")
    if not isinstance(du, dict):
        return
    try:
        from backend.document_understanding.limitations_novelty_profile import (
            extract_limitations_novelty_profile,
        )

        # Narrative LLM output is not Phase 1; leave None unless a future phase attaches it.
        narrative = phases.get("narrative") if isinstance(phases.get("narrative"), dict) else None
        du["limitations_novelty_profile"] = extract_limitations_novelty_profile(
            du, narrative=narrative
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("limitations_novelty_profile extract skipped: %s", exc)
        du["limitations_novelty_profile"] = {
            "schema_version": "1.0.0",
            "has_content": False,
            "error": str(exc),
        }


def _attach_scientific_entities_profile(phases: dict[str, Any]) -> None:
    """Additive scientific_entities_profile on document_understanding (2.6)."""
    du = phases.get("document_understanding")
    if not isinstance(du, dict):
        return
    try:
        from backend.document_understanding.scientific_entities_profile import (
            extract_scientific_entities_profile,
        )

        med = (
            phases.get("medical_understanding")
            if isinstance(phases.get("medical_understanding"), dict)
            else None
        )
        du["scientific_entities_profile"] = extract_scientific_entities_profile(
            du, medical=med
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("scientific_entities_profile extract skipped: %s", exc)
        du["scientific_entities_profile"] = {
            "schema_version": "1.0.0",
            "has_content": False,
            "error": str(exc),
        }


def _attach_quality_assessment_profile(phases: dict[str, Any]) -> None:
    """Additive quality_assessment_profile on document_understanding (2.7)."""
    du = phases.get("document_understanding")
    if not isinstance(du, dict):
        return
    try:
        from backend.document_understanding.quality_assessment_profile import (
            extract_quality_assessment_profile,
        )

        du["quality_assessment_profile"] = extract_quality_assessment_profile(du)
    except Exception as exc:  # noqa: BLE001
        log.warning("quality_assessment_profile extract skipped: %s", exc)
        du["quality_assessment_profile"] = {
            "schema_version": "1.0.0",
            "has_content": False,
            "scoring": "inspectable_checklist",
            "error": str(exc),
        }


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _serialize_document(document: Any, options: AnalysisOptions) -> Any:
    payload = to_jsonable(document, max_str=options.max_full_text_chars)
    # Paper Analysis 2.1 — additive scientific framing (no extra LLM / PDF parse).
    if isinstance(payload, dict):
        try:
            from backend.document_understanding.scientific_structure import (
                extract_scientific_structure,
            )

            payload["scientific_structure"] = extract_scientific_structure(payload)
        except Exception as exc:  # noqa: BLE001 — never fail Phase 1.1 on framing extract
            log.warning("scientific_structure extract skipped: %s", exc)
            payload["scientific_structure"] = {
                "schema_version": "1.0.0",
                "section_skeleton": [],
                "objectives": [],
                "research_questions": [],
                "hypotheses": [],
                "problem_statement": None,
                "error": str(exc),
            }
    return payload


def extract_bibliographic_fields(phase_results: dict[str, Any]) -> dict[str, str]:
    """Pull UserFile-compatible metadata from Phase 1.1 document_understanding."""
    doc = phase_results.get("document_understanding") or {}
    meta = doc.get("metadata") or {}
    out: dict[str, str] = {}
    title = meta.get("title") or ""
    if title:
        out["title"] = str(title)[:500]
    authors = meta.get("authors") or []
    if isinstance(authors, list) and authors:
        out["authors"] = "; ".join(str(a) for a in authors)[:1000]
    elif isinstance(authors, str) and authors:
        out["authors"] = authors[:1000]
    year = meta.get("publication_year") or meta.get("year") or ""
    if year:
        out["year"] = str(year)[:10]
    venue = meta.get("journal") or meta.get("venue") or ""
    if venue:
        out["venue"] = str(venue)[:300]
    doi = meta.get("doi") or ""
    if doi:
        out["doi"] = str(doi)[:200]
    abstract = meta.get("abstract") or ""
    if abstract:
        out["abstract"] = str(abstract)[:8000]
    return out
