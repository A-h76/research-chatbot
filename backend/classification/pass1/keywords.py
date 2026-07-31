"""Keyword and venue lists for Pass 1 classification — the one place new
domains/document types/publication-type signals get added (rule: "avoid
hardcoded constants; place mappings, keyword lists, and rules in
dedicated files"). domain.py/type.py/publication.py never hardcode a
keyword or venue name; they only ever read these dicts through rules.py's
matching functions.

Every dict here is keyed by a member of models.py's DOMAINS/DOCUMENT_TYPES/
PUBLICATION_TYPES tuples (never "other" — "other" is the classifiers' own
fallback when nothing matches, not a set of keywords to match against).
"""

# ------------------------------------------------------------ domain
# Case-insensitive substrings checked against a document's title +
# abstract + full text (see domain.py).
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "medical": [
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
    "computer_science": [
        "algorithm",
        "neural network",
        "machine learning",
        "deep learning",
        "software",
        "computation",
        "programming",
        "artificial intelligence",
        "benchmark dataset",
        "large language model",
    ],
    "physics": [
        "quantum",
        "particle physics",
        "relativity",
        "electromagnetic",
        "thermodynamics",
        "astrophysics",
        "cosmology",
        "wavefunction",
    ],
    "economics": [
        "economic growth",
        "market equilibrium",
        "gdp",
        "inflation",
        "monetary policy",
        "econometric",
        "fiscal policy",
        "labor market",
    ],
    "law": [
        "statute",
        "legal doctrine",
        "court ruling",
        "jurisdiction",
        "litigation",
        "constitutional",
        "plaintiff",
        "defendant",
        "case law",
    ],
    "education": [
        "pedagogy",
        "curriculum",
        "student learning",
        "classroom",
        "teaching method",
        "educational outcomes",
        "learning outcomes",
    ],
    "engineering": [
        "prototype",
        "actuator",
        "control system",
        "sensor array",
        "finite element",
        "circuit design",
        "robotics",
        "mechanical stress",
    ],
    "biology": [
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
    "chemistry": [
        "synthesis",
        "chemical compound",
        "reaction mechanism",
        "catalyst",
        "molecule",
        "spectroscopy",
        "chemical bond",
    ],
    "psychology": [
        "behavioral",
        "cognitive",
        "participants completed",
        "questionnaire",
        "psychological",
        "anxiety",
        "depression",
        "personality trait",
    ],
    "social_sciences": [
        "society",
        "public policy",
        "demographic",
        "socioeconomic",
        "social structure",
        "community",
        "inequality",
        "governance",
    ],
}

# Case-insensitive substrings checked against a document's venue string.
DOMAIN_VENUES: dict[str, list[str]] = {
    "medical": ["lancet", "nejm", "jama", "bmj", "nature medicine"],
    "computer_science": ["neurips", "icml", "iclr", "acl", "cvpr", "aaai"],
    "physics": ["physical review", "nature physics", "arxiv"],
    "economics": ["journal of economic", "econometrica", "quarterly journal of economics"],
    "law": ["law review", "journal of legal studies"],
    "education": ["journal of education", "educational researcher"],
    "engineering": ["ieee", "asme"],
    "biology": ["cell", "nature", "science", "pnas", "elife"],
    "chemistry": ["jacs", "angewandte chemie", "chemical science"],
    "psychology": ["psychological science", "journal of personality"],
    "social_sciences": ["american sociological review", "journal of politics"],
}

# ------------------------------------------------------------ document type
# Case-insensitive substrings checked against title + abstract + full text.
DOCUMENT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "research_article": [
        "we conducted",
        "we performed",
        "our results show",
        "data were collected",
        "sample size",
        "statistically significant",
    ],
    "clinical_guideline": [
        "clinical practice guideline",
        "practice guideline",
        "consensus statement",
        "should be treated with",
        "grade of recommendation",
        "strength of recommendation",
        "we recommend that",
        "guideline panel",
    ],
    "review": [
        "systematic review",
        "meta-analysis",
        "literature review",
        "we reviewed the literature",
        "narrative review",
    ],
    "case_report": [
        "case report",
        "case series",
        "presented with",
        "we describe a case",
        "a patient presented",
    ],
    "protocol": [
        "study protocol",
        "trial registration",
        "this protocol describes",
        "planned statistical analysis",
        "protocol registered",
    ],
    "dataset_paper": [
        "we release",
        "benchmark dataset",
        "data descriptor",
        "corpus of",
        "dataset consists of",
    ],
    "white_paper": [
        "white paper",
        "industry perspective",
        "this paper outlines",
    ],
    "position_paper": [
        "position paper",
        "we argue that",
        "in this position paper",
        "we contend",
    ],
    "conference_paper": [
        "accepted at",
        "in proceedings of",
        "conference paper",
    ],
    "thesis": [
        "submitted in partial fulfillment",
        "a thesis submitted",
        "doctoral dissertation",
        "master's thesis",
    ],
    "preprint": [
        "preprint",
        "not yet peer reviewed",
        "arxiv",
        "biorxiv",
        "medrxiv",
    ],
    "report": [
        "technical report",
        "annual report",
        "report prepared for",
    ],
    "editorial": [
        "editorial",
        "in this editorial",
        "commentary",
        "opinion piece",
    ],
}

# Structural features (backend.processing.models.DocumentQuality's has_*
# flags) expected for each document type — DocumentTypeClassifier scores
# a type by the fraction of its own expected flags that are True. Types
# with no strong structural signature of their own (thesis, preprint,
# white_paper, position_paper, editorial, report, conference_paper) are
# simply absent here; keyword/venue signals carry those instead.
DOCUMENT_TYPE_STRUCTURAL_FEATURES: dict[str, tuple[str, ...]] = {
    "research_article": ("has_methods", "has_results", "has_discussion"),
    # clinical_guideline is keyword-led — has_discussion alone false-positives
    # almost every paper (aligned with pass2 PR-C).
    "review": ("has_abstract", "has_discussion"),
    "case_report": ("has_abstract",),
    "protocol": ("has_methods",),
    "dataset_paper": ("has_methods", "has_results"),
}

# ------------------------------------------------------------ publication type
# Case-insensitive substrings checked against a document's venue string.
PUBLICATION_TYPE_VENUES: dict[str, list[str]] = {
    "journal_article": ["journal of", "transactions on", "the lancet", "nejm", "jama", "bmj"],
    "conference_paper": ["proceedings of", "conference on", "neurips", "icml", "iclr", "symposium on"],
    "book_chapter": ["in:", "chapter in", "edited volume"],
}

# Case-insensitive substrings checked against title + abstract + full text.
PUBLICATION_TYPE_KEYWORDS: dict[str, list[str]] = {
    "preprint": ["arxiv", "biorxiv", "medrxiv", "ssrn", "preprint", "not yet peer reviewed"],
    "thesis": ["submitted in partial fulfillment", "doctoral dissertation", "master's thesis", "a thesis submitted"],
    "report": ["technical report", "annual report"],
    "white_paper": ["white paper"],
}

# document_type (as classified by DocumentTypeClassifier, which runs
# before PublicationTypeClassifier per the Pass 1 pipeline order) is
# itself a weak corroborating signal for publication_type — a document
# already classified as a "thesis"/"preprint"/"conference_paper" document
# type is very likely the matching publication type too.
DOCUMENT_TYPE_TO_PUBLICATION_TYPE: dict[str, str] = {
    "thesis": "thesis",
    "preprint": "preprint",
    "conference_paper": "conference_paper",
    "report": "report",
    "white_paper": "white_paper",
}
