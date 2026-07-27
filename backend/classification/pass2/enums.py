"""Closed label sets for Pass 2 classification — string Enums (see
backend.document_understanding.enums' own docstring for why: a typo in a
comparison fails at the call site instead of silently never matching,
and each still serializes as its plain string value anywhere this app
JSON-dumps a dataclass field).

Distinct from pass1.models' DOMAINS/DOCUMENT_TYPES/PUBLICATION_TYPES
tuples — Pass 2 consumes backend.document_understanding.ProcessedDocument
(composed sub-models, enum-keyed sections) rather than Pass 1's
backend.processing.ProcessedDocument (flat, string-keyed), and its label
sets are richer (e.g. StudyDesign/ReportingGuideline have no Pass 1
equivalent at all) — see package docstring for the full reuse/rebuild
reasoning.
"""

from enum import Enum


class DocumentType(str, Enum):
    RESEARCH_ARTICLE = "research_article"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    CLINICAL_GUIDELINE = "clinical_guideline"
    EDITORIAL = "editorial"
    LETTER = "letter"
    CASE_REPORT = "case_report"
    PROTOCOL = "protocol"
    BOOK_CHAPTER = "book_chapter"
    THESIS = "thesis"
    WHITE_PAPER = "white_paper"
    TECHNICAL_REPORT = "technical_report"
    SURVEY = "survey"
    PREPRINT = "preprint"
    UNKNOWN = "unknown"


class ScientificDomain(str, Enum):
    MEDICINE = "medicine"
    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"
    COMPUTER_SCIENCE = "computer_science"
    AI_ML = "ai_ml"
    CYBER_SECURITY = "cyber_security"
    MATHEMATICS = "mathematics"
    ECONOMICS = "economics"
    PSYCHOLOGY = "psychology"
    ENGINEERING = "engineering"
    SOCIAL_SCIENCE = "social_science"
    MULTIDISCIPLINARY = "multidisciplinary"
    UNKNOWN = "unknown"


class StudyDesign(str, Enum):
    # Medical / life sciences
    RCT = "rct"
    OBSERVATIONAL = "observational"
    COHORT = "cohort"
    CASE_CONTROL = "case_control"
    CROSS_SECTIONAL = "cross_sectional"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    DIAGNOSTIC = "diagnostic"
    QUALITATIVE = "qualitative"
    MIXED_METHODS = "mixed_methods"
    BENCH_EXPERIMENT = "bench_experiment"
    # Computer science / engineering
    ALGORITHM = "algorithm"
    BENCHMARK = "benchmark"
    SYSTEM = "system"
    FRAMEWORK = "framework"
    DATASET = "dataset"
    MODEL = "model"
    SURVEY = "survey"
    UNKNOWN = "unknown"


class ReportingGuideline(str, Enum):
    CONSORT = "consort"  # RCTs
    PRISMA = "prisma"  # Systematic reviews / meta-analyses
    STROBE = "strobe"  # Observational studies
    CARE = "care"  # Case reports
    STARD = "stard"  # Diagnostic accuracy
    SPIRIT = "spirit"  # Trial protocols
    TRIPOD = "tripod"  # Prediction model studies
    ARRIVE = "arrive"  # Animal research
    CHEERS = "cheers"  # Health economic evaluations
    NONE = "none"  # No reporting guideline expected/applicable
    UNKNOWN = "unknown"  # A guideline may apply but none was detected
