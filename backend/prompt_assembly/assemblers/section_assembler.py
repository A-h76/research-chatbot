"""Assembles prioritized section text from ProcessedDocument."""

from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import ProcessedDocument

from ..config import PromptAssemblyConfig
from ..security.limits import ResourceGuard
from ..security.sanitizers import ContentSanitizer


class SectionAssembler:
    def __init__(self, config: PromptAssemblyConfig) -> None:
        self._config = config
        self._guard = ResourceGuard(config)
        self._sanitizer = ContentSanitizer(
            max_length=config.max_section_length,
            strip_html_tags=config.strip_html,
        )

    def assemble(
        self,
        document: ProcessedDocument,
        priorities: list[SectionType],
    ) -> dict[SectionType, str]:
        sections: dict[SectionType, str] = {}
        for section_type in priorities:
            text = document.structure.normalized_headings.get(section_type, "")
            if not text.strip():
                continue
            text = self._guard.clamp_section(text)
            if self._config.sanitize_user_content:
                text = self._sanitizer.sanitize(text)
            sections[section_type] = text
        return sections
