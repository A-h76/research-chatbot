"""Keyword, venue, structural-feature, and cross-label correlation data
for Pass 2 classification — the one place new labels' signals get added
(same "no hardcoded constants" rule pass1.keywords follows). document_type.py/
domain.py/study_design.py/reporting_guideline.py never hardcode a keyword,
venue, or section name; they only read these dicts through pass1.rules'
matching functions (imported, not reimplemented — see package docstring).

Ported from pass1.keywords, not wrapped: pass1's dicts are keyed by its
own DOMAINS/DOCUMENT_TYPES string tuples, a different (and for domain/
document_type, differently-shaped) label set from this package's own
enums.py — see package docstring's reuse table for which labels carry
over directly vs. are genuinely new (StudyDesign/ReportingGuideline have
no pass1 equivalent at all). Every dict here is keyed by a member of this
package's own enums (DocumentType/ScientificDomain/StudyDesign/
ReportingGuideline), never a bare string.
"""

from backend.classification.pass1.rules import match_keywords
from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import ProcessedDocument

from .enums import DocumentType, ReportingGuideline, ScientificDomain, StudyDesign

# ------------------------------------------------------------ document type
# Case-insensitive substrings checked against title + abstract + full_text.
DOCUMENT_TYPE_KEYWORDS: dict[DocumentType, list[str]] = {
    DocumentType.RESEARCH_ARTICLE: [
        "we conducted",
        "we performed",
        "our results show",
        "data were collected",
        "sample size",
        "statistically significant",
    ],
    DocumentType.SYSTEMATIC_REVIEW: [
        "systematic review",
        "prisma",
        "search strategy",
        "included studies",
        "study selection",
        "risk of bias assessment",
    ],
    DocumentType.META_ANALYSIS: [
        "meta-analysis",
        "meta analysis",
        "forest plot",
        "pooled estimate",
        "heterogeneity",
        "random-effects model",
        "fixed-effects model",
    ],
    # Narrative / literature reviews — distinct from systematic_review and
    # from clinical_guideline. Bare "guideline"/"recommendation" used to
    # steal these into CLINICAL_GUIDELINE (PR-C).
    DocumentType.NARRATIVE_REVIEW: [
        "narrative review",
        "literature review",
        "scoping review",
        "we reviewed the literature",
        "this review summarizes",
        "this review provides an overview",
        "in this review we",
        "overview of the literature",
    ],
    DocumentType.CLINICAL_GUIDELINE: [
        "clinical practice guideline",
        "practice guideline",
        "consensus statement",
        "should be treated with",
        "grade of recommendation",
        "strength of recommendation",
        "we recommend that",
        "guideline panel",
    ],
    DocumentType.EDITORIAL: [
        "editorial",
        "in this editorial",
        "commentary",
        "opinion piece",
    ],
    DocumentType.LETTER: [
        "letter to the editor",
        "we read with interest",
        "in response to",
        "correspondence",
    ],
    DocumentType.CASE_REPORT: [
        "case report",
        "case series",
        "presented with",
        "we describe a case",
        "a patient presented",
    ],
    DocumentType.PROTOCOL: [
        "study protocol",
        "trial registration",
        "this protocol describes",
        "planned statistical analysis",
        "protocol registered",
    ],
    DocumentType.BOOK_CHAPTER: [
        "this chapter",
        "in this volume",
        "edited volume",
        "chapter in",
    ],
    DocumentType.THESIS: [
        "submitted in partial fulfillment",
        "a thesis submitted",
        "doctoral dissertation",
        "master's thesis",
    ],
    DocumentType.WHITE_PAPER: [
        "white paper",
        "industry perspective",
        "this paper outlines",
    ],
    DocumentType.TECHNICAL_REPORT: [
        "technical report",
        "annual report",
        "report prepared for",
    ],
    DocumentType.SURVEY: [
        "survey of",
        "we survey",
        "in this survey",
        "comprehensive survey",
        "taxonomy of",
    ],
    DocumentType.PREPRINT: [
        "preprint",
        "not yet peer reviewed",
        "arxiv",
        "biorxiv",
        "medrxiv",
    ],
}

# Structural features (backend.document_understanding's own
# DocumentStructure.normalized_headings keys) expected for each document
# type — DocumentTypeDetector scores a type by the fraction of its own
# expected SectionTypes actually present. Types with no strong structural
# signature of their own (editorial, letter, book_chapter, thesis,
# white_paper, technical_report, survey, preprint) are simply absent
# here; keyword signals carry those instead (matches pass1's identical
# documented choice for the same reason).
DOCUMENT_TYPE_STRUCTURAL_FEATURES: dict[DocumentType, tuple[SectionType, ...]] = {
    DocumentType.RESEARCH_ARTICLE: (SectionType.METHODS, SectionType.RESULTS, SectionType.DISCUSSION),
    DocumentType.SYSTEMATIC_REVIEW: (SectionType.METHODS, SectionType.DISCUSSION),
    DocumentType.META_ANALYSIS: (SectionType.METHODS, SectionType.RESULTS),
    # Narrative reviews are keyword-led; DISCUSSION alone is shared by almost
    # every scholarly paper and previously inflated clinical_guideline.
    DocumentType.NARRATIVE_REVIEW: (SectionType.INTRODUCTION, SectionType.DISCUSSION),
    DocumentType.CASE_REPORT: (SectionType.ABSTRACT,),
    DocumentType.PROTOCOL: (SectionType.METHODS,),
}

# ------------------------------------------------------------ scientific domain
# Case-insensitive substrings checked against title + abstract + full_text.
DOMAIN_KEYWORDS: dict[ScientificDomain, list[str]] = {
    ScientificDomain.MEDICINE: [
        "patient",
        "clinical",
        "disease",
        "treatment",
        "therapy",
        "diagnosis",
        "hospital",
        "physician",
        "nursing",
        "pharmacy",
        "dental",
        "dentistry",
        "surgical",
        "medicine",
    ],
    ScientificDomain.BIOLOGY: [
        "gene expression",
        "protein structure",
        "dna sequence",
        "rna",
        "cell culture",
        "organism",
        "evolutionary",
        "genome",
        "ecology",
    ],
    ScientificDomain.CHEMISTRY: [
        "synthesis",
        "chemical compound",
        "reaction mechanism",
        "catalyst",
        "molecule",
        "spectroscopy",
        "chemical bond",
    ],
    ScientificDomain.PHYSICS: [
        "quantum",
        "particle physics",
        "relativity",
        "electromagnetic",
        "thermodynamics",
        "astrophysics",
        "cosmology",
        "wavefunction",
    ],
    ScientificDomain.COMPUTER_SCIENCE: [
        "algorithm",
        "software",
        "computation",
        "programming",
        "computer science",
        "data structure",
        "distributed system",
        "operating system",
        "database",
    ],
    ScientificDomain.AI_ML: [
        "neural network",
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "large language model",
        "transformer",
        "reinforcement learning",
        "supervised learning",
        "gradient descent",
    ],
    ScientificDomain.CYBER_SECURITY: [
        "vulnerability",
        "malware",
        "exploit",
        "penetration testing",
        "encryption",
        "cyberattack",
        "intrusion detection",
        "threat model",
        "zero-day",
    ],
    ScientificDomain.MATHEMATICS: [
        "theorem",
        "proof",
        "lemma",
        "corollary",
        "conjecture",
        "topology",
        "abstract algebra",
        "number theory",
    ],
    ScientificDomain.ECONOMICS: [
        "economic growth",
        "market equilibrium",
        "gdp",
        "inflation",
        "monetary policy",
        "econometric",
        "fiscal policy",
        "labor market",
    ],
    ScientificDomain.PSYCHOLOGY: [
        "behavioral",
        "cognitive",
        "participants completed",
        "questionnaire",
        "psychological",
        "anxiety",
        "depression",
        "personality trait",
    ],
    ScientificDomain.ENGINEERING: [
        "prototype",
        "actuator",
        "control system",
        "sensor array",
        "finite element",
        "circuit design",
        "robotics",
        "mechanical stress",
    ],
    ScientificDomain.SOCIAL_SCIENCE: [
        "society",
        "public policy",
        "demographic",
        "socioeconomic",
        "social structure",
        "community",
        "inequality",
        "governance",
    ],
    ScientificDomain.MULTIDISCIPLINARY: [
        "interdisciplinary",
        "multidisciplinary",
        "cross-disciplinary",
        "convergence research",
    ],
}

# Case-insensitive substrings checked against the document's venue string
# (metadata.venue/journal/conference — see domain.py).
DOMAIN_VENUES: dict[ScientificDomain, list[str]] = {
    ScientificDomain.MEDICINE: ["lancet", "nejm", "jama", "bmj", "nature medicine"],
    ScientificDomain.BIOLOGY: ["cell", "nature", "science", "pnas", "elife"],
    ScientificDomain.CHEMISTRY: ["jacs", "angewandte chemie", "chemical science"],
    ScientificDomain.PHYSICS: ["physical review", "nature physics", "arxiv"],
    ScientificDomain.COMPUTER_SCIENCE: ["ieee", "acm"],
    ScientificDomain.AI_ML: ["neurips", "icml", "iclr", "cvpr", "aaai", "acl"],
    ScientificDomain.CYBER_SECURITY: ["ieee security", "usenix security", "acm ccs"],
    ScientificDomain.MATHEMATICS: ["annals of mathematics", "journal of the ams", "inventiones mathematicae"],
    ScientificDomain.ECONOMICS: ["journal of economic", "econometrica", "quarterly journal of economics"],
    ScientificDomain.PSYCHOLOGY: ["psychological science", "journal of personality"],
    ScientificDomain.ENGINEERING: ["asme"],
    ScientificDomain.SOCIAL_SCIENCE: ["american sociological review", "journal of politics"],
}

# ------------------------------------------------------------ study design
# Case-insensitive substrings checked against title + abstract + full_text.
STUDY_DESIGN_KEYWORDS: dict[StudyDesign, list[str]] = {
    StudyDesign.RCT: [
        "randomized controlled trial",
        "randomised controlled trial",
        "double-blind",
        "placebo-controlled",
        "random allocation",
        "randomly assigned",
    ],
    StudyDesign.OBSERVATIONAL: [
        "observational study",
        "observational design",
        "we observed",
    ],
    StudyDesign.COHORT: [
        "cohort study",
        "prospective cohort",
        "retrospective cohort",
        "followed over time",
        "longitudinal cohort",
    ],
    StudyDesign.CASE_CONTROL: [
        "case-control study",
        "case control study",
        "matched controls",
        "cases and controls",
    ],
    StudyDesign.CROSS_SECTIONAL: [
        "cross-sectional study",
        "cross sectional survey",
        "at a single point in time",
    ],
    StudyDesign.SYSTEMATIC_REVIEW: [
        "systematic review",
        "prisma",
        "search strategy",
        "study selection",
    ],
    StudyDesign.META_ANALYSIS: [
        "meta-analysis",
        "meta analysis",
        "forest plot",
        "pooled estimate",
        "heterogeneity",
    ],
    StudyDesign.NARRATIVE_REVIEW: [
        # Keep this list short so a single decisive phrase clears
        # CONFIDENCE_THRESHOLD (match weight = hits / len(list)).
        "narrative review",
        "literature review",
        "scoping review",
    ],
    StudyDesign.DIAGNOSTIC: [
        "diagnostic accuracy",
        "sensitivity and specificity",
        "receiver operating characteristic",
        "index test",
        "reference standard",
    ],
    StudyDesign.QUALITATIVE: [
        "qualitative study",
        "thematic analysis",
        "grounded theory",
        "semi-structured interviews",
        "focus groups",
    ],
    StudyDesign.MIXED_METHODS: [
        "mixed methods",
        "mixed-methods design",
        "quantitative and qualitative",
    ],
    StudyDesign.BENCH_EXPERIMENT: [
        "in vitro",
        "in vivo",
        "cell culture",
        "wet lab",
        "laboratory experiment",
        "assay",
    ],
    StudyDesign.ALGORITHM: [
        "we propose an algorithm",
        "algorithmic complexity",
        "time complexity",
        "pseudocode",
    ],
    StudyDesign.BENCHMARK: [
        "benchmark dataset",
        "we benchmark",
        "baseline comparison",
        "leaderboard",
    ],
    StudyDesign.SYSTEM: [
        "we present a system",
        "system architecture",
        "implementation details",
        "system design",
    ],
    StudyDesign.FRAMEWORK: [
        "we propose a framework",
        "conceptual framework",
        "theoretical framework",
        "architectural framework",
    ],
    StudyDesign.DATASET: [
        "we release a dataset",
        "dataset consists of",
        "data descriptor",
        "corpus of",
    ],
    StudyDesign.MODEL: [
        "we train a model",
        "model architecture",
        "pretrained model",
        "fine-tuned",
    ],
    StudyDesign.SURVEY: [
        "survey of",
        "we survey",
        "taxonomy of",
        "comprehensive survey",
    ],
}

# ------------------------------------------------------------ reporting guideline
# Case-insensitive substrings checked against title + abstract + full_text.
# Mostly literal checklist name/acronym matches — deliberately multi-word
# for CARE/SPIRIT/CHEERS (bare "care"/"spirit"/"cheers" are common English
# words and would false-positive constantly as a single-token match).
REPORTING_GUIDELINE_KEYWORDS: dict[ReportingGuideline, list[str]] = {
    ReportingGuideline.CONSORT: ["consort statement", "consort checklist", "consort flow diagram", "consort 20"],
    ReportingGuideline.PRISMA: ["prisma statement", "prisma checklist", "prisma flow diagram", "prisma 20"],
    ReportingGuideline.STROBE: ["strobe statement", "strobe checklist"],
    ReportingGuideline.CARE: ["care guidelines", "care checklist", "care case report guideline"],
    ReportingGuideline.STARD: ["stard statement", "stard checklist"],
    ReportingGuideline.SPIRIT: ["spirit statement", "spirit checklist", "spirit guideline"],
    ReportingGuideline.TRIPOD: ["tripod statement", "tripod checklist"],
    ReportingGuideline.ARRIVE: ["arrive guidelines", "arrive checklist"],
    ReportingGuideline.CHEERS: ["cheers statement", "cheers checklist"],
}

# A document's already-classified study_design strongly corroborates a
# reporting guideline (an RCT is expected to follow CONSORT even if the
# word "CONSORT" itself never appears in the extracted text — e.g. it
# only appeared in a supplementary checklist file, not the body) — see
# reporting_guideline.py, which uses this the same way pass1.publication
# uses DOCUMENT_TYPE_TO_PUBLICATION_TYPE.
STUDY_DESIGN_TO_REPORTING_GUIDELINE: dict[StudyDesign, ReportingGuideline] = {
    StudyDesign.RCT: ReportingGuideline.CONSORT,
    StudyDesign.SYSTEMATIC_REVIEW: ReportingGuideline.PRISMA,
    StudyDesign.META_ANALYSIS: ReportingGuideline.PRISMA,
    StudyDesign.OBSERVATIONAL: ReportingGuideline.STROBE,
    StudyDesign.COHORT: ReportingGuideline.STROBE,
    StudyDesign.CASE_CONTROL: ReportingGuideline.STROBE,
    StudyDesign.CROSS_SECTIONAL: ReportingGuideline.STROBE,
    StudyDesign.DIAGNOSTIC: ReportingGuideline.STARD,
}

# Same idea, from the already-classified document_type (protocol/case
# report have no StudyDesign member of their own but do have a clear
# guideline — SPIRIT/CARE respectively).
DOCUMENT_TYPE_TO_REPORTING_GUIDELINE: dict[DocumentType, ReportingGuideline] = {
    DocumentType.PROTOCOL: ReportingGuideline.SPIRIT,
    DocumentType.CASE_REPORT: ReportingGuideline.CARE,
}

# ------------------------------------------------------------ flat keyword overview
# Primary Topics / key_themes should be subject-matter terms, not classifier
# chrome ("editorial", "framework for", "consort statement"). Document-type,
# study-design, and reporting-guideline phrases stay on their detectors'
# evidence lists — they must not pollute the topic overview (PR-C follow-up).

_TOPIC_KEYWORD_MAPS = (DOMAIN_KEYWORDS,)


def extract_detected_keywords(document: ProcessedDocument) -> list[str]:
    """Domain keyword phrases found in title + abstract + full_text.

    Deduplicated, first-seen order preserved. Deliberately excludes
    document-type / study-design / reporting-guideline lexicon so Primary
    Topics stays researcher-facing.
    """
    text = f"{document.metadata.title}\n{document.metadata.abstract}\n{document.full_text}"

    seen: list[str] = []
    seen_set: set[str] = set()
    for keyword_map in _TOPIC_KEYWORD_MAPS:
        for signal in match_keywords(text, keyword_map).values():
            for term in signal.matched_terms:
                if term not in seen_set:
                    seen_set.add(term)
                    seen.append(term)
    return seen
