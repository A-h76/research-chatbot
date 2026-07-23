"""Default prompt content for prompts this app's own code depends on
existing (not just user-authored ones) — extract_metadata and
paper_analysis, consumed by worker.py's queue handlers AND server.py's
synchronous POST /api/documents/<id>/analysis endpoint; semantic_search,
consumed by POST /api/rag.

Lives here, not in either of those two files, because neither can import
from the other: worker.py does `import server` (safe — it's a standalone
process, never imported back); server.py importing FROM worker.py would
mean worker.py's own `import server` line runs again during that import,
re-executing the whole file under a second module identity (the same
recursion problem documented throughout this project — see
auth/magic_link.py's docstring for the canonical explanation). This
module imports neither, so both can import from it safely.

Jinja2-native, NOT copies of server.py's _META_PROMPT/_ANALYSIS_PROMPT —
those use Python str.format() placeholders ({excerpt}) and, for the
analysis prompt, literally-escaped {{term: ...}} JSON-example syntax.
Both are real PromptRegistry failure modes, verified directly against a
real Template(...) call: a bare {excerpt} passes through unrendered
(real text never reaches the model), and {{term: ...}} hard-crashes
(Jinja2 reads double braces as a variable expression, not an escaped
literal). Same field names/shape as the originals — downstream JSON
parsing depends on them; the JSON-example portions are described in
prose instead of embedded brace syntax to sidestep the crash entirely.
"""

EXTRACT_METADATA_PROMPT = """You are a metadata extractor for academic papers.

Given the first portion of a research document, extract the following fields exactly as they appear. Return ONLY a JSON object — no markdown, no prose. Use null for any field you cannot find with high confidence.

Fields:
  title       - full paper title (string or null)
  authors     - semicolon-separated author names, "Last, F." style (string or null)
  year        - 4-digit publication year (string or null)
  venue       - journal, conference, or publisher name (string or null)
  doi         - DOI string without the "https://doi.org/" prefix (string or null)
  abstract    - full abstract text verbatim (string or null)
  keywords    - comma-separated keywords if listed (string or null)

Document excerpt (first {{ max_chars }} characters):
{{ excerpt }}
"""

PAPER_ANALYSIS_PROMPT = """You are an expert research analyst. Analyse the paper below and return ONLY a JSON object — no markdown fences, no prose outside the object.

Each key maps to the content described. Use null when a section genuinely does not apply (e.g. no dataset for a pure theory paper). Never fabricate details not present in the text.

Keys and what to put in them:
  executive_summary   - 3-5 sentences: what is this paper, why does it matter
  abstract_explained  - rewrite the abstract for a smart non-specialist
  research_objective  - one sentence: what the paper is trying to achieve
  problem_statement   - the specific gap or problem being addressed
  methodology         - how the study was conducted (approach, framework, steps)
  dataset              - datasets used, sizes, sources (null if not applicable)
  experiments          - key experiments or evaluations described
  results              - main findings; include numbers if stated
  key_contributions    - a JSON array of strings, each a distinct novel contribution
  strengths            - what the paper does particularly well, as an array of strings
  limitations          - weaknesses, assumptions, threats to validity, as an array
  future_work          - next steps suggested by authors or implied by gaps, as an array
  keywords              - 5-10 technical keywords as a JSON array
  important_terms       - a JSON object mapping each key technical term to a one-line definition

Paper text (first {{ max_chars }} characters):
{{ text }}
"""

# Verbatim copy of backend/ai/seed.py's own "semantic_search" text —
# not a rewrite. seed.py's seed_prompts() and this module's
# ensure_default_prompts() can both independently manage this same
# prompt name safely only because they agree on the exact content;
# ensure_prompt() is idempotent by comparing text, so if either diverged
# even slightly the two would fight over which version is active every
# time either one runs.
SEMANTIC_SEARCH_PROMPT = (
    "Given these documents, answer the following question using only "
    "information found in them. Cite which document each fact comes "
    "from.\n\nDocuments:\n{{ documents }}\n\nQuestion: {{ question }}"
)

META_EXCERPT_CHARS = 3_000
ANALYSIS_MAX_CHARS = 12_000

# A model asked for "a JSON array" doesn't always return one (a bare
# string, or omits the key) — downstream code (the analysis UI, export)
# assumes these are always the right Python type.
ANALYSIS_ARRAY_FIELDS = (
    "key_contributions",
    "strengths",
    "limitations",
    "future_work",
    "keywords",
)


def ensure_prompt(registry, name, template_text):
    """Idempotent: a no-op once the active version already matches (checked
    by content, not just presence) — safe to call on every startup/request
    without piling up a new version row each time.

    status="active" is required on both branches now: PromptRegistry's
    default status is "draft" (migration 0015's authoring lifecycle — see
    docs/prompt-engine-architecture.md §3), and a draft version is not
    servable via get_prompt()'s no-explicit-version path. This function's
    whole job is "make sure this exact template is the one served", so it
    always means to activate it, not leave it pending review."""
    active = registry.get_active_version(name)
    if active and active.template == template_text:
        return
    if active:
        registry.add_version(name, template_text, is_active=True, status="active")
    else:
        registry.create_prompt(name, f"default prompt: {name}", template_text, status="active")


def ensure_default_prompts(db_session):
    from .prompt_registry import PromptRegistry

    registry = PromptRegistry(db_session)
    ensure_prompt(registry, "extract_metadata", EXTRACT_METADATA_PROMPT)
    ensure_prompt(registry, "paper_analysis", PAPER_ANALYSIS_PROMPT)
    ensure_prompt(registry, "semantic_search", SEMANTIC_SEARCH_PROMPT)
