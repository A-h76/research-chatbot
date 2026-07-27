"""Main prompt assembler — template fill, token limits, system+user split."""

from backend.analysis_context.enums import PromptFamily, PromptStrategy

from ..config import PromptAssemblyConfig
from ..enums import PromptComponentType
from ..models import AssemblyLog, AssembledPrompt, ConfidenceScore, DocumentContext, PromptComponent
from ..security.limits import TokenLimiter, estimate_tokens
from ..security.sanitizers import ContentSanitizer, safe_fill_template
from ..templates import ALLOWED_TEMPLATE_KEYS, get_template
from .confidence_filter import filter_by_confidence


class PromptAssembler:
    """Main prompt assembler."""

    def __init__(self, config: PromptAssemblyConfig) -> None:
        self.config = config
        self._limiter = TokenLimiter(config)
        self._sanitizer = ContentSanitizer(
            max_length=config.max_prompt_length,
            strip_html_tags=config.strip_html,
        )

    def assemble(
        self,
        components: list[PromptComponent],
        template_name: str,
        strategy: PromptStrategy,
        family: PromptFamily,
        document_context: DocumentContext,
        extra_variables: dict[str, str] | None = None,
    ) -> AssembledPrompt:
        log = AssemblyLog(template_used=template_name)
        sorted_components = sorted(components, key=lambda c: c.priority)
        filtered, filter_result = filter_by_confidence(sorted_components, self.config)
        log.add_decision("confidence_filter", filter_result.rationale, confidence=1.0)

        by_type = {c.component_type: c for c in filtered}
        variables = self._build_variables(by_type, document_context, extra_variables or {})

        system_template, user_template = get_template(template_name)
        system_prompt = safe_fill_template(system_template, variables, ALLOWED_TEMPLATE_KEYS)
        user_prompt = safe_fill_template(user_template, variables, ALLOWED_TEMPLATE_KEYS)

        # Soft-enforce system budget by truncating if needed
        system_tokens = estimate_tokens(system_prompt, self.config.token_estimation_strategy)
        if system_tokens > self.config.max_system_prompt_tokens:
            max_chars = self.config.max_system_prompt_tokens * 4
            system_prompt = system_prompt[:max_chars]
            log.add_decision("truncate_system", f"system prompt truncated to ~{self.config.max_system_prompt_tokens} tokens")

        user_prompt, user_truncated = self._limiter.check_and_truncate(user_prompt)
        if user_truncated:
            log.add_decision("truncate_user", f"user prompt truncated to ~{self.config.max_total_prompt_tokens} tokens")

        full_prompt = system_prompt + "\n\n" + user_prompt
        full_prompt, full_truncated = self._limiter.check_and_truncate(full_prompt)
        if full_truncated:
            log.add_decision("truncate_full", "full prompt truncated to token budget")

        if len(full_prompt) > self.config.max_prompt_length:
            full_prompt = full_prompt[: self.config.max_prompt_length]
            log.add_decision("clamp_length", f"full prompt clamped to {self.config.max_prompt_length} chars")

        tokens = estimate_tokens(full_prompt, self.config.token_estimation_strategy)
        log.component_count = len(filtered)
        log.tokens_estimated = tokens

        evidence_included = []
        for component in filtered:
            evidence_included.extend(component.evidence)

        confidences = [c.confidence for c in filtered]
        component_mean = sum(confidences) / len(confidences) if confidences else 0.0
        coverage = min(1.0, len(filtered) / max(1, len(components)))
        confidence = ConfidenceScore.calculate(
            component_mean=component_mean,
            coverage=coverage,
            profile_confidence=1.0,
            sanitization_ok=1.0 if self.config.sanitize_user_content else 0.8,
        )

        return AssembledPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            full_prompt=full_prompt,
            components=filtered,
            sections=document_context.key_sections,
            document_context=document_context,
            evidence_included=evidence_included,
            confidence_score=confidence,
            prompt_family=family,
            prompt_strategy=strategy,
            max_tokens=self.config.max_total_prompt_tokens,
            temperature=self.config.default_temperature,
            assembly_log=log,
        )

    def _build_variables(
        self,
        by_type: dict[PromptComponentType, PromptComponent],
        document_context: DocumentContext,
        extra: dict[str, str],
    ) -> dict[str, str]:
        def content(ctype: PromptComponentType, default: str = "") -> str:
            component = by_type.get(ctype)
            return component.content if component is not None else default

        variables = {
            "title": document_context.title or "",
            "authors": ", ".join(document_context.authors),
            "journal": document_context.journal or "",
            "year": str(document_context.publication_year) if document_context.publication_year is not None else "",
            "doi": document_context.doi or "",
            "abstract": document_context.abstract or "",
            "document_context": content(PromptComponentType.DOCUMENT_CONTEXT),
            "task_description": content(PromptComponentType.TASK_DESCRIPTION),
            "clinical_entities": content(PromptComponentType.CLINICAL_ENTITIES),
            "pico": content(PromptComponentType.PICO),
            "statistics": content(PromptComponentType.STATISTICS),
            "grading": content(PromptComponentType.GRADING),
            "evidence": content(PromptComponentType.EVIDENCE),
            "instructions": content(PromptComponentType.INSTRUCTION),
            "output_format": content(PromptComponentType.OUTPUT_FORMAT),
            "nct_number": str(document_context.metadata.get("clinical_trials_id") or ""),
            "study_design": extra.get("study_design", ""),
            "population": extra.get("population", content(PromptComponentType.PICO)),
            "intervention": extra.get("intervention", ""),
            "comparator": extra.get("comparator", ""),
            "outcomes": extra.get("outcomes", ""),
            "results": content(PromptComponentType.STATISTICS),
            "risk_of_bias": extra.get("risk_of_bias", content(PromptComponentType.GRADING)),
            "review_question": extra.get("review_question", ""),
            "grade_assessment": content(PromptComponentType.GRADING),
            "synthesis": content(PromptComponentType.EVIDENCE),
            "method": extra.get("method", ""),
            "contributions": extra.get("contributions", ""),
        }
        # Values already sanitized in builders; re-sanitize extras defensively.
        if self.config.sanitize_user_content:
            for key, value in list(variables.items()):
                if key in ("task_description", "instructions", "output_format"):
                    continue  # trusted static strings
                variables[key] = self._sanitizer.sanitize(value)
        return variables
