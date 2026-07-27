"""Prompt templates keyed by family name.

Templates use `{placeholder}` syntax filled exclusively via
security.sanitizers.safe_fill_template (whitelist + sanitized values) —
never str.format with document text.
"""

from .clinical import CLINICAL_TRIAL_TEMPLATE, CLINICAL_SYSTEM
from .cs_ai import CS_AI_SYSTEM, CS_AI_TEMPLATE
from .generic import GENERIC_SYSTEM, GENERIC_TEMPLATE
from .medical import MEDICAL_SYSTEM, MEDICAL_TEMPLATE
from .methodological import METHODOLOGICAL_SYSTEM, METHODOLOGICAL_TEMPLATE
from .systematic import SYSTEMATIC_REVIEW_TEMPLATE, SYSTEMATIC_SYSTEM

TEMPLATES: dict[str, tuple[str, str]] = {
    "medical": (MEDICAL_SYSTEM, MEDICAL_TEMPLATE),
    "clinical": (CLINICAL_SYSTEM, CLINICAL_TRIAL_TEMPLATE),
    "systematic": (SYSTEMATIC_SYSTEM, SYSTEMATIC_REVIEW_TEMPLATE),
    "methodological": (METHODOLOGICAL_SYSTEM, METHODOLOGICAL_TEMPLATE),
    "cs_ai": (CS_AI_SYSTEM, CS_AI_TEMPLATE),
    "generic": (GENERIC_SYSTEM, GENERIC_TEMPLATE),
}

# Whitelisted placeholder keys every template may use.
ALLOWED_TEMPLATE_KEYS = frozenset(
    {
        "title",
        "authors",
        "journal",
        "year",
        "doi",
        "abstract",
        "task_description",
        "clinical_entities",
        "pico",
        "statistics",
        "grading",
        "evidence",
        "instructions",
        "output_format",
        "document_context",
        "nct_number",
        "study_design",
        "population",
        "intervention",
        "comparator",
        "outcomes",
        "results",
        "risk_of_bias",
        "review_question",
        "grade_assessment",
        "synthesis",
        "method",
        "contributions",
    }
)


def get_template(name: str) -> tuple[str, str]:
    return TEMPLATES.get(name, TEMPLATES["generic"])
