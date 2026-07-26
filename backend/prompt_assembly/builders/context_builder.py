"""Builds the document-context PromptComponent and DocumentContext model."""

from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import PromptAssemblyConfig
from ..enums import PromptComponentType, PromptPriority
from ..interfaces import BasePromptBuilder
from ..models import DocumentContext, PromptComponent
from ..security.limits import ResourceGuard
from ..security.sanitizers import ContentSanitizer


class ContextBuilder(BasePromptBuilder):
    """Builds document context component."""

    def __init__(self, config: Optional[PromptAssemblyConfig] = None) -> None:
        self._config = config or PromptAssemblyConfig()
        self._guard = ResourceGuard(self._config)
        self._sanitizer = ContentSanitizer(
            max_length=self._config.max_prompt_length,
            strip_html_tags=self._config.strip_html,
        )

    def build(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        context: AnalysisContext,
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> PromptComponent:
        doc_ctx = self.build_document_context(document, context)
        lines = [
            f"Title: {doc_ctx.title or '(untitled)'}",
            f"Authors: {', '.join(doc_ctx.authors) if doc_ctx.authors else '(unknown)'}",
            f"Journal: {doc_ctx.journal or '(unknown)'}",
            f"Year: {doc_ctx.publication_year if doc_ctx.publication_year is not None else '(unknown)'}",
            f"DOI: {doc_ctx.doi or '(unknown)'}",
            f"Document type: {classification.document_type.label.value}",
            f"Domain: {classification.domain.label.value}",
            f"Study design: {classification.study_design.label.value}",
            "",
            "Abstract:",
            doc_ctx.abstract or "(not available)",
        ]
        content = "\n".join(lines)
        if self._config.sanitize_user_content:
            content = self._sanitizer.sanitize(content)

        return PromptComponent(
            component_type=PromptComponentType.DOCUMENT_CONTEXT,
            content=content,
            priority=1,
            confidence=1.0,
            evidence=[],
            source="ContextBuilder",
            priority_level=PromptPriority.CRITICAL,
        )

    def build_document_context(
        self, document: ProcessedDocument, context: AnalysisContext
    ) -> DocumentContext:
        meta = document.metadata
        abstract = self._guard.clamp_abstract(meta.abstract or "")
        if self._config.sanitize_user_content:
            abstract = self._sanitizer.sanitize(abstract)

        key_sections: dict[SectionType, str] = {}
        priorities = context.prompt_profile.section_priorities or [
            SectionType.ABSTRACT,
            SectionType.METHODS,
            SectionType.RESULTS,
        ]
        for section_type in priorities[:6]:
            text = document.structure.normalized_headings.get(section_type, "")
            if not text:
                continue
            text = self._guard.clamp_section(text)
            if self._config.sanitize_user_content:
                text = self._sanitizer.sanitize(text)
            key_sections[section_type] = text

        return DocumentContext(
            title=self._sanitizer.sanitize(meta.title) if self._config.sanitize_user_content else meta.title,
            authors=list(meta.authors),
            publication_year=meta.publication_year,
            journal=meta.journal or meta.venue or None,
            doi=meta.doi,
            abstract=abstract,
            summary=None,
            key_sections=key_sections,
            metadata={
                "clinical_trials_id": meta.clinical_trials_id,
                "pmid": meta.pmid,
                "language": meta.language.value if meta.language else None,
            },
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        return 100

    def component_type(self) -> PromptComponentType:
        return PromptComponentType.DOCUMENT_CONTEXT
