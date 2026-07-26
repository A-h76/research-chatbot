"""DomainRegistry — detects which research domain a paper belongs to
(medical, ai_ml, biology, ...) and looks up the domain-specific
PromptVersion name to use for it.

Pure Python, no DB session anywhere — DOMAINS is a static class-level
dict, not a table, and every method operates on it plus whatever
metadata/content string a caller passes in. This is deliberate, not an
oversight: unlike PersonaEngine/MemoryEngine/PromptRegistry (all of
which read real rows), nothing here needs a Session to answer "does this
paper look medical or AI/ML" — that's a config lookup + substring match,
not a query. is_domain_available() only checks the static `enabled`
flag for the same reason — it is NOT a live "has this been seeded in
prompt_versions yet" check (that would need a PromptRegistry/Session
this class deliberately doesn't take).

"general" is the one domain whose prompt_name points at the real,
already-seeded "paper_analysis" prompt (backend/ai/prompts.py /
backfill.py) rather than a new "domain_general" — a fallback domain
that means "nothing more specific applies" should reuse the existing
default analysis prompt, not require a second, redundant one seeded
just for symmetry with the other eight names.
"""

from typing import Any, Dict, List, Optional


class DomainRegistry:
    # Document TYPE (research paper vs. clinical guide vs. review, ...) is a
    # different axis from DOMAIN (medical vs. ai_ml, ...) below — a "medical"
    # paper can be a randomized trial, a systematic review, or a how-to
    # guide, and the right analysis framing differs for each regardless of
    # domain. Order matters here the same way it does for DOMAINS' own
    # keyword lists below: first-match-wins, most-specific-first, so a case
    # report that happens to mention "study" still lands on "case_report"
    # rather than the much more generic "research".
    DOCUMENT_TYPE_KEYWORDS: Dict[str, List[str]] = {
        "case_report": ["case report", "case series", "presented with"],
        "review": ["systematic review", "meta-analysis", "literature review"],
        "editorial": ["editorial", "opinion", "commentary"],
        "clinical_guide": [
            "guide",
            "clinical guide",
            "practical guide",
            "how to",
            "step by step",
            "recommendation",
        ],
        "research": [
            "randomized",
            "controlled trial",
            "cohort",
            "study",
            "data analysis",
            "clinical trial",
        ],
    }

    DOMAINS: Dict[str, Dict[str, Any]] = {
        "medical": {
            "name": "medical",
            "label": "Medical and Allied Health Sciences",
            "description": "Clinical medicine, nursing, and allied health research.",
            "prompt_name": "domain_medical",
            "enabled": True,
            "keywords": [
                "rct",
                "randomized",
                "clinical trial",
                "patient",
                "hospital",
                "drug",
                "therapy",
                "diagnosis",
                "treatment",
            ],
            "venues": ["lancet", "nejm", "jama", "bmj", "nature medicine"],
        },
        "ai_ml": {
            "name": "ai_ml",
            "label": "Computer Science / AI / Machine Learning",
            "description": "Artificial intelligence, machine learning, and computer science research.",
            "prompt_name": "domain_ai_ml",
            "enabled": True,
            "keywords": [
                "neural network",
                "deep learning",
                "benchmark",
                "model",
                "training",
                "dataset",
                "accuracy",
                "f1",
                "llm",
            ],
            "venues": ["neurips", "icml", "iclr", "acl", "cvpr", "aaai"],
        },
        "biology": {
            "name": "biology",
            "label": "Biology and Life Sciences",
            "description": "Molecular biology, genetics, and life sciences research.",
            "prompt_name": "domain_biology",
            "enabled": True,
            "keywords": [
                "gene",
                "protein",
                "dna",
                "rna",
                "cell",
                "molecular",
                "organism",
                "evolution",
            ],
            "venues": ["cell", "nature", "science", "pnas", "elife"],
        },
        "psychology": {
            "name": "psychology",
            "label": "Psychology and Behavioral Sciences",
            "description": "Cognitive, clinical, and behavioral psychology research.",
            "prompt_name": "domain_psychology",
            "enabled": True,
            "keywords": [
                "behavior",
                "cognitive",
                "participants",
                "questionnaire",
                "psychological",
                "anxiety",
                "depression",
                "personality",
            ],
            "venues": ["psychological science", "journal of personality", "apa"],
        },
        "engineering": {
            "name": "engineering",
            "label": "Engineering and Applied Sciences",
            "description": "Mechanical, electrical, civil, and applied engineering research.",
            "prompt_name": "domain_engineering",
            "enabled": True,
            "keywords": [
                "prototype",
                "actuator",
                "control system",
                "sensor",
                "finite element",
                "circuit",
                "mechanical stress",
            ],
            "venues": ["ieee", "asme", "elsevier"],
        },
        "social_sciences": {
            "name": "social_sciences",
            "label": "Social Sciences",
            "description": "Sociology, political science, economics, and related fields.",
            "prompt_name": "domain_social_sciences",
            "enabled": True,
            "keywords": [
                "society",
                "policy",
                "demographic",
                "socioeconomic",
                "social",
                "community",
                "inequality",
                "governance",
            ],
            "venues": ["american sociological review", "journal of politics"],
        },
        "chemistry": {
            "name": "chemistry",
            "label": "Chemistry",
            "description": "Organic, inorganic, and physical chemistry research.",
            "prompt_name": "domain_chemistry",
            "enabled": True,
            "keywords": [
                "synthesis",
                "compound",
                "reaction",
                "catalyst",
                "molecule",
                "spectroscopy",
                "chemical bond",
            ],
            "venues": ["jacs", "angewandte chemie", "chemical science"],
        },
        "physics": {
            "name": "physics",
            "label": "Physics",
            "description": "Theoretical and experimental physics research.",
            "prompt_name": "domain_physics",
            "enabled": True,
            "keywords": [
                "quantum",
                "particle",
                "field theory",
                "relativity",
                "electromagnetic",
                "thermodynamics",
                "wavefunction",
            ],
            "venues": ["physical review", "nature physics", "arxiv"],
        },
        "general": {
            "name": "general",
            "label": "General / Unclassified",
            "description": "Fallback for papers that don't match a specific domain.",
            "prompt_name": "paper_analysis",  # reuses the existing default, see module docstring
            "enabled": True,
            "keywords": [],
            "venues": [],
        },
    }

    # ------------------------------------------------------------ reads
    def get_domain(self, name: str) -> Optional[Dict[str, Any]]:
        return self.DOMAINS.get(name)

    def list_domains(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        domains = self.DOMAINS.values()
        if enabled_only:
            domains = [d for d in domains if d["enabled"]]
        return list(domains)

    def get_domain_prompt_name(self, domain: str) -> Optional[str]:
        entry = self.get_domain(domain)
        return entry["prompt_name"] if entry else None

    def is_domain_available(self, domain: str) -> bool:
        """Static `enabled` flag only — not a live "has this actually
        been seeded in prompt_versions" check (see module docstring for
        why: this class deliberately takes no Session)."""
        entry = self.get_domain(domain)
        return bool(entry and entry["enabled"])

    # ------------------------------------------------------------ detection
    def detect_domain(
        self,
        metadata: Optional[Dict[str, Any]] = None,
        content: str = "",
        user_selected: Optional[str] = None,
    ) -> str:
        """Priority: user_selected -> venue match -> keyword match ->
        "general". Every stage only ever considers *enabled* domains —
        detection should never route a paper toward a domain whose
        module isn't actually available."""
        if user_selected is not None and self.is_domain_available(user_selected):
            return user_selected

        venue = ((metadata or {}).get("venue") or "").lower()
        if venue:
            for name, entry in self.DOMAINS.items():
                if not entry["enabled"] or not entry["venues"]:
                    continue
                if any(v in venue for v in entry["venues"]):
                    return name

        # ponytail: first-match-wins substring scan, no scoring — simple
        # and correct for "initially" (the task's own word); upgrade to
        # counting/ranking keyword hits per domain if a paper's content
        # ever plausibly matches two domains' keyword lists at once and
        # first-match-wins picks the wrong one in practice.
        text = (content or "").lower()
        if text:
            for name, entry in self.DOMAINS.items():
                if not entry["enabled"] or not entry["keywords"]:
                    continue
                if any(k in text for k in entry["keywords"]):
                    return name

        return "general"

    def detect_document_type(
        self,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """What kind of document this is (research paper, clinical guide,
        review, case report, editorial), as opposed to detect_domain()'s
        "what field" — orthogonal axes, both usable together (e.g. a
        "medical" "clinical_guide"). Priority: venue/journal match -> title
        + first 500 characters of content (keyword match, see
        DOCUMENT_TYPE_KEYWORDS' own comment for the check order) ->
        "general". Unlike detect_domain(), there's no user_selected
        override or enabled-flag gate — document type isn't a per-domain
        concept with its own on/off switch."""
        meta = metadata or {}

        # A paper published in one of this class's own known peer-reviewed
        # venues (DOMAINS[*]["venues"] below — nejm, lancet, neurips,
        # nature, ...) is, by default, a primary research article rather
        # than a guide or editorial. Reuses the venue lists already
        # maintained for domain detection instead of a second, separately
        # curated list that would drift out of sync with it over time.
        venue = (meta.get("venue") or "").lower()
        if venue:
            known_venues = {v for entry in self.DOMAINS.values() for v in entry["venues"]}
            if any(v in venue for v in known_venues):
                return "research"

        text = f"{meta.get('title') or ''} {(content or '')[:500]}".lower()
        if text.strip():
            for doc_type, keywords in self.DOCUMENT_TYPE_KEYWORDS.items():
                if any(k in text for k in keywords):
                    return doc_type

        return "general"
