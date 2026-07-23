"""Seeds default prompts and model-call presets. Run directly
(python -m backend.ai.seed) or import seed_prompts()/seed_pipelines()
and call with an already-open session (e.g. from server.py on startup).

Both functions are idempotent — safe to call on every startup, not just
once — matching backfill.py's own "checks for existing rows before
inserting" convention.

IMPORTANT — read before assuming this seeds what its name suggests:

seed_prompts() writes into the REAL prompt_versions table via
PromptRegistry, but backfill.py already seeds five prompts there
(extract_metadata, paper_analysis, compare, gap_finder, chat_system) —
real, detailed templates the app's actual code (extract_metadata(),
trigger_paper_analysis(), etc.) depends on. This task's own
"paper_analysis" name collides with that. Seeding here is idempotent BY
NAME: if backfill.py already ran, this function's short "paper_analysis"
stub is skipped, not inserted — the real, live prompt is never
overwritten.

HOWEVER, we have now replaced the short stub with the comprehensive
16-section expert template (the same content previously defined as
PAPER_ANALYSIS_EXPERT). If backfill.py already seeded a real
paper_analysis, this new content will NOT replace it (idempotent by
name). To get the expert version as the default, you must either:
- Run backfill.py after this seed (unlikely), or
- Manually update the existing paper_analysis row via admin UI or SQL.
For fresh installations (where backfill.py hasn't run), this seed will
create the expert version directly.

The other six names (paper_summary, citation_generation, semantic_search,
gap_analysis, comparison, literature_review) don't collide with anything
and seed normally.

seed_pipelines() does NOT write into pipeline_versions — that table
(also already seeded by backfill.py) represents something structurally
different: an import/embedding pipeline bundle (chunking params + a
required FK to a real model_versions row), not a named chat-call preset
like {"model": "gpt-4o", "temperature": 0.7, "max_tokens": 2000}.
Forcing these three presets into pipeline_versions would mean fabricating
a fake embed_model_version_id FK that has nothing to do with what's
actually being seeded. Instead this defines its own small, new
model_presets table — a different, genuinely new concept, not a
duplicate or a rename of pipeline_versions. No migration exists for this
table since nothing else in the schema needs it; this module creates it
if missing (see _ensure_model_presets_table).
"""

import json
import os
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

from .persona_engine import PersonaEngine
from .prompt_registry import Persona, PromptRegistry
from .system_prompt import DEFAULT_SYSTEM_PROMPT, SystemPromptManager

_Base = declarative_base()


def create_model_preset_model(Base):
    class ModelPreset(Base):
        __tablename__ = "model_presets"
        __table_args__ = (UniqueConstraint("name", name="uq_model_presets_name"),)
        id = Column(Integer, primary_key=True)
        name = Column(String(60), nullable=False)
        config = Column(Text, nullable=False)  # JSON: {"model", "temperature", "max_tokens", ...}
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return ModelPreset


ModelPreset = create_model_preset_model(_Base)


# The task's own opening phrases ("Summarize this research paper...")
# are clearly truncated illustrations, not complete templates — expanded
# into full, renderable ones with real Jinja2 variables, matching the
# quality bar of backfill.py's own PROMPTS dict rather than seeding
# literal "..." into the database.
#
# The "paper_analysis" template has been replaced with a comprehensive
# 16-section expert analysis (previously defined as PAPER_ANALYSIS_EXPERT)
# to ensure that even a simple user query ("Analyze this paper") returns
# a rigorous, thesis-ready output.
DEFAULT_PROMPTS = {
    "paper_summary": (
        "Summarize this research paper, covering its main contribution, "
        "methodology, and key findings.\n\nPaper:\n{{ text }}"
    ),
    "paper_analysis": (
        'You are analyzing a research paper. The user has asked: "{{ query }}"\n\n'
        "**Paper Content:**\n{{ text }}\n\n"
        "**Paper Metadata:**\n"
        "- Title: {{ title }}\n"
        "- Authors: {{ authors }}\n"
        "- Year: {{ year }}\n"
        "- Journal/Conference: {{ venue }}\n\n"
        "Provide a comprehensive, expert-level analysis structured in the following 16 sections. "
        "Be rigorous, specific, and actionable.\n\n"
        "## 1. Paper Summary\n"
        "Provide a concise summary of the paper (2-3 paragraphs). What did the authors do? What did they find? Why does it matter?\n\n"
        "## 2. Research Problem & Motivation\n"
        "What problem is the paper trying to solve? Why is this important? What gap does it address?\n\n"
        "## 3. Core Contribution\n"
        "What is the paper's single most important contribution? What's the novel insight or method?\n\n"
        "## 4. Methodology Assessment\n"
        "What methods were used? Are they appropriate for the research question? What are the strengths and weaknesses of the approach?\n\n"
        "## 5. Experimental Design & Validation\n"
        "Is the experimental design sound? What controls are in place? What's missing? Are the conclusions supported by the data?\n\n"
        "## 6. Critical Assumptions\n"
        "What assumptions does the paper make? Are they stated or hidden? How would the results change if these assumptions were violated?\n\n"
        "## 7. Limitations & Weaknesses\n"
        "What are the paper's limitations? What didn't they address? What's the weakest part of the argument?\n\n"
        "## 8. Reproducibility Assessment\n"
        "Can this work be reproduced? What information is missing that would be needed for reproduction?\n\n"
        "## 9. Relationship to Existing Work\n"
        "Does this contradict, confirm, or extend existing research? Which papers would disagree with this conclusion? Why?\n\n"
        "## 10. Hidden Gaps\n"
        "What questions does the paper leave unanswered? What would the authors have investigated if they had unlimited resources?\n\n"
        "## 11. Suggested Extensions\n"
        "What experiments or analyses would strengthen this work? What's the natural next step?\n\n"
        "## 12. Thesis Potential\n"
        "If you are a PhD/Master's student, how could this paper support your thesis? What specific ideas, methods, or findings could you build upon?\n\n"
        "## 13. Literature Review Position\n"
        "Where does this paper fit in the broader literature? What's its place in the research landscape?\n\n"
        "## 14. Practical Implementation Difficulty\n"
        "How difficult would it be to implement this work? What resources, data, or expertise would be required?\n\n"
        "## 15. Real-world Applications\n"
        "What are the practical applications of this work? Who would benefit from it?\n\n"
        "## 16. Overall Assessment & Key Takeaways\n"
        "What's your honest assessment of the paper? Is it a breakthrough, incremental, or flawed? What are the 3 key takeaways?\n\n"
        "**Important Guidelines:**\n"
        "- Be specific and cite evidence from the paper.\n"
        "- Distinguish between facts, interpretations, and suggestions.\n"
        "- If a section is not applicable, state that clearly rather than inventing content.\n"
        "- Never fabricate references or information.\n"
        "- Write at an expert level, suitable for a PhD student.\n\n"
        "Output the response as a structured JSON object with these 16 keys."
    ),
    "citation_generation": (
        "Generate a BibTeX citation for the following paper, using only "
        "the metadata given.\n\nTitle: {{ title }}\nAuthors: {{ authors }}\n"
        "Year: {{ year }}\nVenue: {{ venue }}\nDOI: {{ doi }}"
    ),
    "semantic_search": (
        "Given these documents, answer the following question using only "
        "information found in them. Cite which document each fact comes "
        "from.\n\nDocuments:\n{{ documents }}\n\nQuestion: {{ question }}"
    ),
    "gap_analysis": (
        "Identify research gaps in the following set of papers — "
        "underexplored topics, open questions, and missing experiments.\n\n"
        "Papers:\n{{ papers }}"
    ),
    "comparison": (
        "Compare these two papers in terms of methodology, findings, and "
        "contributions. Note similarities and differences.\n\n"
        "Paper A:\n{{ paper_a }}\n\nPaper B:\n{{ paper_b }}"
    ),
    "literature_review": (
        "Synthesize these papers into a coherent literature review, "
        "identifying common themes, contradictions, and trends.\n\n"
        "Papers:\n{{ papers }}"
    ),
}

DEFAULT_PIPELINES = {
    "gpt-4o-chat": {"model": "gpt-4o", "temperature": 0.7, "max_tokens": 2000},
    "gpt-4o-mini-chat": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1000},
    "gpt-4o-analysis": {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 4000},
}

# DOMAIN_MODULES — additional analysis sections layered onto the core
# 16-section paper_analysis structure, one prompt per research domain.
# Names match backend/ai/domain_registry.py's DomainRegistry.DOMAINS
# exactly (DOMAINS["medical"]["prompt_name"] == "domain_medical", etc.) —
# this is the seed data that name is expected to resolve to once seeded,
# though wiring DomainRegistry's detection into an actual call site is a
# separate, later task, not done here.
#
# Each entry is a COMPLETE, standalone template, not a fragment appended
# at render time: PromptRegistry has no template-composition mechanism —
# get_prompt() renders exactly one named template — so a domain module
# has to repeat the core 16 sections verbatim (same text as
# DEFAULT_PROMPTS["paper_analysis"] above) rather than assume something
# else supplies them, then add its own domain-specific sections after.
_CORE_16_SECTIONS = (
    "## 1. Paper Summary\n"
    "Provide a concise summary of the paper (2-3 paragraphs). What did the authors do? What did they find? Why does it matter?\n\n"
    "## 2. Research Problem & Motivation\n"
    "What problem is the paper trying to solve? Why is this important? What gap does it address?\n\n"
    "## 3. Core Contribution\n"
    "What is the paper's single most important contribution? What's the novel insight or method?\n\n"
    "## 4. Methodology Assessment\n"
    "What methods were used? Are they appropriate for the research question? What are the strengths and weaknesses of the approach?\n\n"
    "## 5. Experimental Design & Validation\n"
    "Is the experimental design sound? What controls are in place? What's missing? Are the conclusions supported by the data?\n\n"
    "## 6. Critical Assumptions\n"
    "What assumptions does the paper make? Are they stated or hidden? How would the results change if these assumptions were violated?\n\n"
    "## 7. Limitations & Weaknesses\n"
    "What are the paper's limitations? What didn't they address? What's the weakest part of the argument?\n\n"
    "## 8. Reproducibility Assessment\n"
    "Can this work be reproduced? What information is missing that would be needed for reproduction?\n\n"
    "## 9. Relationship to Existing Work\n"
    "Does this contradict, confirm, or extend existing research? Which papers would disagree with this conclusion? Why?\n\n"
    "## 10. Hidden Gaps\n"
    "What questions does the paper leave unanswered? What would the authors have investigated if they had unlimited resources?\n\n"
    "## 11. Suggested Extensions\n"
    "What experiments or analyses would strengthen this work? What's the natural next step?\n\n"
    "## 12. Thesis Potential\n"
    "If you are a PhD/Master's student, how could this paper support your thesis? What specific ideas, methods, or findings could you build upon?\n\n"
    "## 13. Literature Review Position\n"
    "Where does this paper fit in the broader literature? What's its place in the research landscape?\n\n"
    "## 14. Practical Implementation Difficulty\n"
    "How difficult would it be to implement this work? What resources, data, or expertise would be required?\n\n"
    "## 15. Real-world Applications\n"
    "What are the practical applications of this work? Who would benefit from it?\n\n"
    "## 16. Overall Assessment & Key Takeaways\n"
    "What's your honest assessment of the paper? Is it a breakthrough, incremental, or flawed? What are the 3 key takeaways?\n\n"
)

_MEDICAL_SECTIONS_17_TO_30 = (
    "## 17. PICO Extraction (Medical)\n"
    "- **P**opulation: Who are the patients/subjects? (age, condition, demographics)\n"
    "- **I**ntervention: What treatment, exposure, or diagnostic test?\n"
    "- **C**omparison: What is the alternative or control?\n"
    "- **O**utcome: What was measured? (primary and secondary outcomes)\n\n"
    "## 18. Evidence Quality (Medical)\n"
    "What study design was used? Assign an evidence level:\n"
    "- Meta-analysis → Very High\n"
    "- Randomized Controlled Trial → High\n"
    "- Cohort Study → Moderate\n"
    "- Case-Control → Moderate\n"
    "- Cross-sectional → Low\n"
    "- Expert Opinion → Very Low\n\n"
    "## 19. Risk of Bias Assessment (Medical)\n"
    "Evaluate:\n"
    "- Selection bias: Was the sample representative?\n"
    "- Performance bias: Were participants/providers blinded?\n"
    "- Detection bias: Were outcome assessors blinded?\n"
    "- Attrition bias: Was follow-up complete?\n"
    "- Reporting bias: Were all outcomes reported?\n"
    "- Funding bias: Who funded the research? Conflicts of interest?\n\n"
    "## 20. Clinical Relevance (Medical)\n"
    "- Which patients benefit from this?\n"
    "- Does it affect diagnosis, treatment, or prevention?\n"
    "- Can hospitals/clinics realistically adopt this?\n"
    "- What is the implementation timeline?\n\n"
    "## 21. Clinical Outcomes (Medical)\n"
    "- Primary outcomes: What was the main measure? Was it achieved?\n"
    "- Secondary outcomes: What else was measured?\n"
    "- Clinical significance: Is the effect meaningful?\n"
    "- Adverse effects: What side effects or harms were reported?\n"
    "- Mortality: Was survival affected?\n"
    "- Quality of life: Was patient quality of life improved?\n"
    "- Hospital stay / Readmission rates\n\n"
    "## 22. Statistical Interpretation (Medical)\n"
    "- Confidence intervals: Are they reported? Are they narrow?\n"
    "- Odds Ratio / Relative Risk / Hazard Ratio\n"
    "- Sensitivity / Specificity / PPV / NPV (for diagnostic studies)\n"
    "- ROC-AUC\n"
    "- P-values: Are they adjusted for multiple comparisons?\n"
    "- Effect sizes: Are they clinically meaningful?\n\n"
    "## 23. Guideline Comparison (Medical)\n"
    "Compare with major guidelines:\n"
    "- WHO, CDC, NICE, AHA, ADA, Local guidelines\n"
    "- Does this agree or differ?\n\n"
    "## 24. GRADE Assessment (Medical)\n"
    "Estimate certainty of evidence:\n"
    "- High, Moderate, Low, Very Low\n\n"
    "## 25. Clinical Translation (Medical)\n"
    "- Can this be used clinically immediately?\n"
    "- Or is it still laboratory/bench research?\n"
    "- Estimated timeline for clinical adoption?\n"
    "- Barriers to translation?\n\n"
    "## 26. Patient Population (Medical)\n"
    "- Sample size: Is it adequate?\n"
    "- Age, gender, ethnicity distribution\n"
    "- Inclusion/exclusion criteria\n"
    "- Generalizability to other populations\n\n"
    "## 27. Safety & Adverse Events (Medical)\n"
    "- Adverse events reported?\n"
    "- Safety profile?\n"
    "- Contraindications?\n"
    "- Monitoring required?\n"
    "- Risk/benefit ratio?\n\n"
    "## 28. Ethics & Patient Consent (Medical)\n"
    "- Ethical approval obtained?\n"
    "- Patient consent?\n"
    "- Vulnerable populations protected?\n"
    "- Data privacy standards?\n"
    "- Clinical trial registration?\n\n"
    "## 29. Cost-effectiveness (Medical)\n"
    "- Cost-effective compared to alternatives?\n"
    "- Implementation costs?\n"
    "- Long-term cost implications?\n"
    "- Feasibility in low-resource settings?\n\n"
    "## 30. Clinical Bottom Line (Medical)\n"
    "- Can clinicians trust this paper?\n"
    "- Would it change current practice?\n"
    "- Should researchers conduct more studies first?\n"
    "- How useful is this for medical education?\n"
    "- Single most important takeaway for a clinician?\n\n"
)

DOMAIN_MODULES = {
    "domain_medical": (
        'You are analyzing a research paper. The user has asked: "{{ query }}"\n\n'
        "**Paper Content:**\n{{ text }}\n\n"
        "**Paper Metadata:**\n"
        "- Title: {{ title }}\n"
        "- Authors: {{ authors }}\n"
        "- Year: {{ year }}\n"
        "- Journal/Conference: {{ venue }}\n\n"
        "Provide a comprehensive, expert-level analysis structured in the following 30 "
        "sections (the core 16 plus 14 medical/clinical-specific sections). Be rigorous, "
        "specific, and actionable, holding this paper to clinical evidence standards.\n\n"
        + _CORE_16_SECTIONS
        + _MEDICAL_SECTIONS_17_TO_30
        + "**Important Guidelines:**\n"
        "- Be specific and cite evidence from the paper.\n"
        "- Distinguish between facts, interpretations, and suggestions.\n"
        "- If a section is not applicable, state that clearly rather than inventing content.\n"
        "- Never fabricate references or information.\n"
        "- Write at an expert level, suitable for a clinician or medical researcher.\n\n"
        "Output the response as a structured JSON object with these 30 keys."
    ),
    # Stub only, per this task's own instruction — the full AI/ML domain
    # module (benchmark rigor, ablations, compute/licensing reporting,
    # etc.) is a separate, later task, not written here.
    "domain_ai_ml": (
        'You are analyzing an AI/ML research paper. The user has asked: "{{ query }}"\n\n'
        "**Paper Content:**\n{{ text }}\n\n"
        "**Paper Metadata:**\n"
        "- Title: {{ title }}\n"
        "- Authors: {{ authors }}\n"
        "- Year: {{ year }}\n"
        "- Journal/Conference: {{ venue }}\n\n"
        "Provide the standard 16-section analysis below, with particular attention to "
        "benchmark validity, dataset quality/bias, reproducibility of reported metrics, "
        "and comparison against reported state-of-the-art baselines.\n\n"
        + _CORE_16_SECTIONS
        + "**Important Guidelines:**\n"
        "- Be specific and cite evidence from the paper.\n"
        "- Distinguish between facts, interpretations, and suggestions.\n"
        "- Never fabricate references or information.\n\n"
        "(Placeholder module — AI/ML-specific sections beyond the core 16 "
        "are not yet written; see backend/ai/seed.py's DOMAIN_MODULES.)"
    ),
}

# The architecture doc (docs/prompt-engine-architecture.md §5.3) only
# fully wrote out two of these eight ("TODO" placeholders for the rest,
# by design — a design doc isn't where prompt copy gets finalized) —
# written out in full here, matching the same tone/length/"what NOT to
# do" framing as the two originals rather than leaving stubs in the
# database.
DEFAULT_PERSONAS = {
    "Research Assistant": {
        "description": "General-purpose research assistant for literature, methodology, and writing help.",
        "system_prompt": (
            "You are a meticulous research assistant helping a PhD student. "
            "Prioritize accuracy over confidence — flag uncertainty rather than "
            "guessing. Cite specific papers/sections when referencing evidence. "
            "Default to concise, structured answers over long prose."
        ),
    },
    "Literature Review Expert": {
        "description": "Synthesizes and critiques literature reviews across multiple papers.",
        "system_prompt": (
            "You are a literature review specialist. Synthesize findings across "
            "multiple papers into coherent themes rather than summarizing each one "
            "in isolation. Explicitly call out contradictions, gaps, and consensus "
            "positions in the literature. Always distinguish between what the "
            "literature actually shows and your own synthesis or interpretation of it."
        ),
    },
    "Academic Editor": {
        "description": "Edits academic writing for clarity, structure, and adherence to conventions.",
        "system_prompt": (
            "You are an academic editor. Improve clarity, structure, and precision "
            "of academic writing without changing its meaning or the author's voice. "
            "Flag ambiguous claims, unsupported assertions, and awkward phrasing "
            "directly — do not silently rewrite around a substantive problem. Follow "
            "the conventions of formal academic prose: no contractions, no "
            "first-person outside methods/discussion sections, precise terminology "
            "over vague language."
        ),
    },
    "Peer Reviewer": {
        "description": "Reviews papers with the rigor of an academic peer-review process.",
        "system_prompt": (
            "You are a rigorous peer reviewer for an academic venue. Identify "
            "methodological weaknesses, unsupported claims, and missing related "
            "work. Be direct and specific — 'the sample size is too small to "
            "support this conclusion' rather than 'consider strengthening this "
            "section.' Never soften a real flaw to be polite."
        ),
    },
    "Methodology Advisor": {
        "description": "Evaluates and advises on research design and methodology.",
        "system_prompt": (
            "You are a methodology advisor for empirical research. Evaluate "
            "whether the proposed or described method actually answers the stated "
            "research question — a valid method for the wrong question is still a "
            "flaw. Identify confounds, validity threats, and sampling issues "
            "explicitly, and suggest concrete alternatives rather than only naming "
            "the problem. Distinguish design issues (fixable before data collection) "
            "from analysis issues (fixable after)."
        ),
    },
    "Statistician": {
        "description": "Reviews statistical methods, tests, and significance claims.",
        "system_prompt": (
            "You are a statistician reviewing research methodology and results. "
            "Check that the statistical tests used actually match the data type, "
            "sample size, and research design — flag mismatches explicitly (e.g. a "
            "parametric test on non-normal data, or multiple comparisons without "
            "correction). Distinguish statistical significance from practical/"
            "effect-size significance. Never confirm a result is valid without "
            "seeing the actual test used and its assumptions."
        ),
    },
    "Writing Coach": {
        "description": "Coaches academic writing for clarity and reader comprehension.",
        "system_prompt": (
            "You are a writing coach for academic authors. Focus on clarity, flow, "
            "and reader comprehension rather than grammar alone. Point out where a "
            "sentence or paragraph asks too much of the reader — buried claims, "
            "unclear antecedents, or paragraphs doing more than one job. Encourage "
            "the author's own voice; suggest revisions as options, not replacements "
            "to adopt verbatim."
        ),
    },
    "Grant Proposal Advisor": {
        "description": "Evaluates grant proposals for significance, feasibility, and clarity.",
        "system_prompt": (
            "You are a grant proposal advisor. Evaluate proposals the way a "
            "funding panel would: is the significance clearly stated in the first "
            "paragraph, is the aims/methods link explicit, and is the budget "
            "justified by the proposed work. Flag vague significance claims, "
            "overly ambitious aims for the timeline/budget given, and any place a "
            "reviewer skimming in five minutes would lose the thread. Be blunt "
            "about weak sections — a proposal that doesn't get funded because of "
            "an avoidable clarity issue is a real failure to prevent."
        ),
    },
}


def seed_prompts(db_session) -> dict:
    """Returns {name: PromptVersion} for all seven default prompts plus
    every DOMAIN_MODULES entry (domain_medical, domain_ai_ml, ...) —
    freshly created ones and pre-existing ones (from this function on a
    prior run, or from backfill.py) alike. Domain modules are seeded
    with category="domain_module" (a shared value across all of them,
    not per-name like the core prompts' category=name below) so they can
    be listed/filtered as a group later; status="active" so they're
    immediately servable, same as every other call in this function."""
    registry = PromptRegistry(db_session)
    result = {}
    for name, template in DEFAULT_PROMPTS.items():
        existing = registry.get_active_version(name)
        if existing:
            print(f"SKIP  prompt '{name}' already seeded (v{existing.version})")
            result[name] = existing
            continue
        result[name] = registry.create_prompt(
            name=name,
            description=f"Default seed prompt: {name}",
            template_text=template,
            status="active",
            category=name,
        )
        print(f"OK    prompt '{name}' seeded")

    for name, template in DOMAIN_MODULES.items():
        existing = registry.get_active_version(name)
        if existing:
            print(f"SKIP  domain module '{name}' already seeded (v{existing.version})")
            result[name] = existing
            continue
        result[name] = registry.create_prompt(
            name=name,
            description=f"Domain module: {name}",
            template_text=template,
            status="active",
            category="domain_module",
        )
        print(f"OK    domain module '{name}' seeded")

    return result


def seed_pipelines(db_session) -> dict:
    """Returns {name: ModelPreset} for the three default chat-call
    presets. Ensures model_presets exists first — see module docstring
    for why this table, not pipeline_versions."""
    _ensure_model_presets_table(db_session)

    result = {}
    for name, config in DEFAULT_PIPELINES.items():
        existing = db_session.query(ModelPreset).filter_by(name=name).first()
        if existing:
            print(f"SKIP  pipeline preset '{name}' already seeded")
            result[name] = existing
            continue
        row = ModelPreset(name=name, config=json.dumps(config))
        db_session.add(row)
        db_session.commit()
        print(f"OK    pipeline preset '{name}' seeded ({config})")
        result[name] = row
    return result


def _ensure_model_presets_table(db_session):
    """No migration creates model_presets (see module docstring) — this
    is the one place responsible for it existing, checked cheaply via
    the bind already on db_session rather than requiring a separate
    engine reference."""
    engine = db_session.get_bind()
    ModelPreset.__table__.create(bind=engine, checkfirst=True)


def seed_system_prompt(db_session):
    """Seeds the default global system prompt (backend/ai/system_prompt.py)
    — idempotent by name, same convention as seed_prompts(). Returns the
    active PromptVersion row (freshly created, or the one already there)."""
    registry = PromptRegistry(db_session)
    existing = registry.get_active_version(SystemPromptManager.NAME)
    if existing:
        print(f"SKIP  system prompt already seeded (v{existing.version})")
        return existing

    SystemPromptManager(registry).set_active_prompt(DEFAULT_SYSTEM_PROMPT)
    active = registry.get_active_version(SystemPromptManager.NAME)
    print("OK    system prompt seeded")
    return active


def seed_personas(db_session) -> dict:
    """Returns {name: Persona} for all eight default personas — idempotent
    by name, same convention as seed_prompts(). Persona itself lives on
    prompt_registry.py's private Base (see that module), not this one —
    Persona is imported from there, not redefined here."""
    engine = PersonaEngine(db_session, Persona)
    result = {}
    for name, spec in DEFAULT_PERSONAS.items():
        existing = engine.get_by_name(name)
        if existing:
            print(f"SKIP  persona '{name}' already seeded")
            result[name] = existing
            continue
        result[name] = engine.create(name, spec["description"], spec["system_prompt"])
        print(f"OK    persona '{name}' seeded")
    return result


def seed_all(db_session) -> dict:
    return {
        "prompts": seed_prompts(db_session),
        "pipelines": seed_pipelines(db_session),
        "system_prompt": seed_system_prompt(db_session),
        "personas": seed_personas(db_session),
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from .prompt_registry import _Base as _prompt_base

    load_dotenv()
    # Same DATABASE_URL / SQLite-fallback convention as backfill.py —
    # standalone engine, not server.py's (avoids `import server`, which
    # would re-execute that file under a second module identity since
    # it runs as __main__ — see auth/magic_link.py's docstring for the
    # full explanation of why that's a hard rule in this project).
    url = (os.environ.get("DATABASE_URL") or "sqlite:///chat_dev.db").replace("postgres://", "postgresql://", 1)
    engine = create_engine(url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    # prompt_versions only exists today via the Postgres-only migration
    # 0005 — never against local SQLite (no ORM class was ever
    # registered under server.py's own Base to trigger its creation
    # there). checkfirst=True makes this a no-op wherever the real
    # migration already ran (any real Postgres deployment); it only
    # actually creates anything on a fresh SQLite dev DB, so this CLI
    # entrypoint works out of the box either way.
    _prompt_base.metadata.create_all(engine, checkfirst=True)

    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
