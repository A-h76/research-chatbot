"""Versioned prompts for project-scoped cross-paper research (Sprint B).

Jinja2-safe: no bare ``{placeholder}`` / double-brace JSON examples.
Rendered via PromptRegistry or a local SandboxedEnvironment fallback.
"""

PROJECT_RESEARCH_PROMPT = """You are a research analyst answering questions across a corpus of papers in one project.

Intent: {{ intent_label }}
{% if query %}Research question: {{ query }}
{% endif %}
Return ONLY a JSON object (no markdown fences) with this shape:
  summary — 1-2 sentence overview suitable for a card preview (concise)
  answer  — coherent prose answering the intent/question using the papers below
  claims  — array of objects, each with:
    claim   — one atomic finding or claim
    support — array of supporting evidence objects, each with:
      paper_id  — integer id of the paper (must be one of the ids listed)
      title     — paper title
      section   — section or analysis field name when known (e.g. methodology, results, limitations), else empty string
      snippet   — short quote or paraphrase from that paper's analysis (1-2 sentences)
      citation  — short citation like "FirstAuthor Year"

Rules:
- Every claim must have at least one support entry with a valid paper_id from the corpus.
- Prefer disagreements, methodological contrasts, and evidence strength when the intent asks for them.
- Do not invent papers or paper_ids. Do not claim facts absent from the analyses.
- If evidence is thin, say so in answer and still cite what exists.

Paper corpus (JSON array):
{{ papers_json }}
"""

# Human-readable labels for internal intents (never shown as API field names).
INTENT_LABELS = {
    "compare": "Compare the papers: similarities, differences, and synthesis",
    "disagree": "Where do these papers disagree or contradict each other?",
    "datasets": "What datasets and data sources appear, and how do they compare?",
    "methodology": "Which methodology is strongest, and why?",
    "evidence": "Summarise the evidence across these papers",
    "open_questions": "What questions remain unanswered across these papers?",
    "freeform": "Answer the researcher's freeform question using the papers",
}

# Public preset → internal intent
PRESET_TO_INTENT = {
    "compare": "compare",
    "disagree": "disagree",
    "datasets": "datasets",
    "methodology": "methodology",
    "evidence": "evidence",
    "open_questions": "open_questions",
}

VALID_PRESETS = frozenset(PRESET_TO_INTENT.keys())
