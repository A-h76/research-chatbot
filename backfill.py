"""Backfill + seed script — run once, immediately after run_migrations.py,
against a database that has real `files` rows but empty new tables.

Every section is idempotent (checks for existing rows before inserting),
so an accidental second run is a no-op, not a duplicate-data bug.
"""

import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = (os.environ.get("DATABASE_URL") or "sqlite:///chat_dev.db").replace(
    "postgres://", "postgresql://", 1
)
engine = create_engine(url, pool_pre_ping=True)

# Prompt templates copied verbatim from server.py's module-level prompt
# constants (_META_PROMPT, _ANALYSIS_PROMPT, _COMPARE_PROMPT, _GAP_PROMPT).
# chat_system is the one exception: there is no flat template for it in
# the codebase — build_system_prompt() assembles the real system prompt
# dynamically (user name, date, custom instructions, project, memories).
# What's seeded here is only its static, unconditional opening sentence;
# it is not the complete prompt a chat turn actually sends.
PROMPTS = {
    "extract_metadata": """You are a metadata extractor for academic papers.

Given the first portion of a research document, extract the following fields
exactly as they appear.  Return ONLY a JSON object — no markdown, no prose.
Use null for any field you cannot find with high confidence.

Fields:
  title       – full paper title (string | null)
  authors     – semicolon-separated author names, "Last, F." style (string | null)
  year        – 4-digit publication year (string | null)
  venue       – journal, conference, or publisher name (string | null)
  doi         – DOI string without "https://doi.org/" prefix (string | null)
  abstract    – full abstract text verbatim (string | null)
  keywords    – comma-separated keywords if listed (string | null)

Document excerpt (first 3 000 chars):
{excerpt}
""",
    "paper_analysis": """You are an expert research analyst. Analyse the paper below and return ONLY a JSON object — no markdown fences, no prose outside the object.

Each key maps to the content described. Use null when a section genuinely does not apply (e.g. no dataset for a pure theory paper). Never fabricate details not present in the text.

Keys and what to put in them:
  executive_summary   – 3–5 sentences: what is this paper, why does it matter
  abstract_explained  – rewrite the abstract for a smart non-specialist
  research_objective  – one sentence: what the paper is trying to achieve
  problem_statement   – the specific gap or problem being addressed
  methodology         – how the study was conducted (approach, framework, steps)
  dataset             – datasets used, sizes, sources (null if not applicable)
  experiments         – key experiments or evaluations described
  results             – main findings; include numbers if stated
  key_contributions   – JSON array of strings, each a distinct novel contribution
  strengths           – what the paper does particularly well (array of strings)
  limitations         – weaknesses, assumptions, threats to validity (array)
  future_work         – next steps suggested by authors or implied by gaps (array)
  keywords            – 5–10 technical keywords as a JSON array
  important_terms     – JSON object {{term: one-line definition}} for key jargon

Paper text (first {max_chars} characters):
{text}
""",
    "compare": """You are an expert research analyst comparing multiple academic papers.

Given the structured analyses of {n} papers below, produce a JSON object with the following keys. Use null for any section that genuinely cannot be answered from the provided analyses. Never fabricate. Be specific.

Keys:
  overview         – 2-3 sentence description of what these papers share and how they differ
  similarities     – array of strings: themes, approaches, or findings common to ALL papers
  differences      – array of strings: key ways the papers diverge (method, scope, results)
  common_datasets  – array of dataset names used by 2 or more papers ([] if none)
  methodologies    – object {{paper_title: one-line methodology summary}} for each paper
  agreements       – array: claims or conclusions the papers agree on
  contradictions   – array: claims or findings that conflict across papers
  research_trends  – array: patterns or directions evident across the set
  synthesis        – 3-5 sentences: what does reading these papers together reveal?

Papers (as structured analyses):
{analyses}
""",
    "gap_finder": """You are an expert research analyst identifying gaps, open questions, and opportunities across a set of academic papers.

Given the structured analyses of {n} papers, produce a JSON object with the keys below. Base every finding strictly on the provided content — never fabricate gaps, assumptions, or ideas. If you are uncertain, say so rather than inventing something.

IMPORTANT: Label all output explicitly as AI-generated suggestions, not factual claims. This is enforced in the output keys themselves.

Keys:
  preamble              – 1-2 sentences: what field / subfield these papers cover
  underexplored_topics  – array of strings: topics the papers acknowledge but do not thoroughly investigate
  missing_experiments   – array of strings: experiments that would strengthen claims but are absent from these papers
  open_questions        – array of strings: explicit research questions raised but not resolved across the set
  methodological_gaps   – array of strings: limitations in methods used that future work should address
  dataset_gaps          – array of strings: missing data, domains, or populations not studied
  potential_thesis_ideas– array of strings: concrete thesis/dissertation topics a researcher could pursue based on these gaps
  future_opportunities  – array of strings: promising research directions emerging from the combined findings
  disclaimer            – MUST equal exactly: "These are AI-generated suggestions based on the provided paper analyses. They should be treated as starting points for your own critical assessment, not as definitive research conclusions."

Papers (as structured analyses):
{analyses}
""",
    "chat_system": (
        "You are Personal AI, a helpful assistant specialised in academic "
        "research and thesis writing, but able to help with anything. "
        "Use markdown. Be precise with citations and honest about "
        "uncertainty. When you used web search results or document excerpts, "
        "cite the sources inline."
    ),
}

MODELS = {
    "default_model": os.environ.get("DEFAULT_MODEL", "gpt-5-mini"),
    "utility_model": os.environ.get("UTILITY_MODEL", "gpt-4o-mini"),
    "embed_model": os.environ.get("EMBED_MODEL", "text-embedding-3-small"),
}

with engine.begin() as conn:
    # upload_batches: intentionally not backfilled — no batch concept
    # existed before this schema, leave upload_jobs.upload_batch_id NULL
    # for every pre-cutover job rather than fabricating batches that
    # never happened.

    # upload_jobs: one synthetic 'done' import job per file that has
    # extracted text, one synthetic extract_metadata job per file whose
    # metadata extraction already ran — using created_at as the best
    # available stand-in for timing that was never recorded.
    if conn.execute(text("SELECT count(*) FROM upload_jobs")).scalar() == 0:
        conn.execute(text("""
            INSERT INTO upload_jobs (file_id, user_id, job_type, status, started_at, finished_at, created_at)
            SELECT id, user_id, 'import', 'done', created_at, created_at, created_at
            FROM files WHERE text_len > 0
        """))
        conn.execute(text("""
            INSERT INTO upload_jobs (file_id, user_id, job_type, status, started_at, finished_at, created_at)
            SELECT id, user_id, 'extract_metadata', meta_status, created_at, created_at, created_at
            FROM files WHERE meta_status IN ('done', 'failed')
        """))
        print("OK    upload_jobs backfilled")
    else:
        print("SKIP  upload_jobs already has rows")

    # storage_usage: a straight SUM over existing files.
    if conn.execute(text("SELECT count(*) FROM storage_usage")).scalar() == 0:
        conn.execute(text("""
            INSERT INTO storage_usage (user_id, bytes_used, file_count)
            SELECT user_id, sum(size), count(*) FROM files GROUP BY user_id
        """))
        print("OK    storage_usage backfilled")
    else:
        print("SKIP  storage_usage already has rows")

    # prompt_versions: version 1 = today's literal prompt text, active.
    prompt_ids = {}
    for name, template in PROMPTS.items():
        row = conn.execute(
            text("SELECT id FROM prompt_versions WHERE name = :n AND version = 1"),
            {"n": name},
        ).first()
        if row:
            prompt_ids[name] = row[0]
            print(f"SKIP  prompt_versions.{name} v1 already seeded")
            continue
        prompt_ids[name] = conn.execute(
            text("""
            INSERT INTO prompt_versions (name, version, template, is_active)
            VALUES (:n, 1, :t, true) RETURNING id
        """),
            {"n": name, "t": template},
        ).scalar()
        print(f"OK    prompt_versions.{name} v1 seeded (id={prompt_ids[name]})")

    # model_versions: version 1 = today's .env model choices, active.
    model_ids = {}
    for logical_name, provider_model_id in MODELS.items():
        row = conn.execute(
            text(
                "SELECT id FROM model_versions WHERE logical_name = :n AND version = 1"
            ),
            {"n": logical_name},
        ).first()
        if row:
            model_ids[logical_name] = row[0]
            print(f"SKIP  model_versions.{logical_name} v1 already seeded")
            continue
        model_ids[logical_name] = conn.execute(
            text("""
            INSERT INTO model_versions (logical_name, provider_model_id, version, is_active)
            VALUES (:n, :m, 1, true) RETURNING id
        """),
            {"n": logical_name, "m": provider_model_id},
        ).scalar()
        print(
            f"OK    model_versions.{logical_name} v1 seeded "
            f"(id={model_ids[logical_name]}, model={provider_model_id})"
        )

    # pipeline_versions: version 1 = the bundle the seeds above represent.
    if (
        conn.execute(
            text("SELECT count(*) FROM pipeline_versions WHERE version = 1")
        ).scalar()
        == 0
    ):
        conn.execute(
            text("""
            INSERT INTO pipeline_versions
                (version, importer_registry_version, chunking_params,
                 embed_model_version_id, utility_model_version_id, prompt_versions, is_active)
            VALUES (1, 'v1', :chunking, :embed_id, :utility_id, :prompts, true)
        """),
            {
                "chunking": json.dumps({"size": 1500, "overlap": 200}),
                "embed_id": model_ids["embed_model"],
                "utility_id": model_ids["utility_model"],
                "prompts": json.dumps(prompt_ids),
            },
        )
        print("OK    pipeline_versions v1 seeded")
    else:
        print("SKIP  pipeline_versions v1 already seeded")

print(
    "\nai_usage_ledger, outbox_events, feature_flags: left empty — no backfill for any of them."
)
