"""Tests for PromptBuilder against real dependencies (real PromptRegistry,
PersonaEngine, MemoryEngine, SystemPromptManager) over an in-memory
SQLite DB — same "real classes, not mocks" convention as
backend/ai/test_persona_engine.py / test_memory_engine.py, since this
class is pure orchestration over already-tested pieces; mocking all four
would just test that the mocks were called, not that assembly is correct.

Run: pytest backend/ai/test_prompt_builder.py -v
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, DateTime, Integer, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.ai.domain_registry import DomainRegistry
from backend.ai.memory_engine import MemoryEngine
from backend.ai.persona_engine import PersonaEngine
from backend.ai.prompt_builder import PromptBuilder
from backend.ai.prompt_registry import Persona, PromptRegistry
from backend.ai.prompt_registry import _Base as prompt_base
from backend.ai.system_prompt import SystemPromptManager


@pytest.fixture
def env():
    engine = create_engine("sqlite:///:memory:")
    prompt_base.metadata.create_all(engine)  # prompt_versions + personas

    ServerBase = declarative_base()

    class Memory(ServerBase):
        __tablename__ = "memories"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)
        project_id = Column(Integer, nullable=True)
        fact = Column(Text, nullable=False)
        importance = Column(Integer, default=3)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    class Project(ServerBase):
        __tablename__ = "projects"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=True)
        name = Column(Text, default="")
        description = Column(Text, default="")
        instructions = Column(Text, default="")

    ServerBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    registry = PromptRegistry(db)
    system_prompt_manager = SystemPromptManager(registry)
    system_prompt_manager.set_active_prompt("Global system prompt text.")

    persona_engine = PersonaEngine(db, Persona)
    memory_engine = MemoryEngine(db, Memory)
    domain_registry = DomainRegistry()

    builder = PromptBuilder(
        system_prompt_manager=system_prompt_manager,
        persona_engine=persona_engine,
        memory_engine=memory_engine,
        prompt_registry=registry,
        SessionLocal=SessionLocal,
        Project=Project,
        domain_registry=domain_registry,
    )

    return {
        "db": db,
        "SessionLocal": SessionLocal,
        "Memory": Memory,
        "Project": Project,
        "registry": registry,
        "persona_engine": persona_engine,
        "domain_registry": domain_registry,
        "builder": builder,
    }


def _make_task(env, name="ask", template="Answer the question: {{ query }}"):
    env["registry"].create_prompt(name, "test task", template, status="active")


# ------------------------------------------------------------ assembly / ordering
def test_build_assembles_minimal_prompt_system_then_task(env):
    _make_task(env)
    result = env["builder"].build("what is X?", "ask")

    assert result.system == "Global system prompt text."
    assert result.task == "Answer the question: what is X?"
    assert result.final == ("## System\nGlobal system prompt text.\n\n" "## Task\nAnswer the question: what is X?")


def test_build_omits_empty_sections_from_final(env):
    _make_task(env)
    result = env["builder"].build("q", "ask")

    assert "## Persona" not in result.final
    assert "## Project Context" not in result.final
    assert "## Memory" not in result.final
    assert "## Retrieved Context" not in result.final
    assert "## Output Format" not in result.final


def test_build_section_order_is_system_persona_project_memory_rag_task_schema(env):
    _make_task(env)
    env["persona_engine"].create("Reviewer", "d", "You are a reviewer.")
    proj = env["Project"](user_id=1, description="A project about widgets.")
    env["db"].add(proj)
    env["db"].commit()
    env["db"].add(env["Memory"](user_id=1, fact="likes widgets"))
    env["db"].commit()

    result = env["builder"].build(
        "q",
        "ask",
        persona="Reviewer",
        project_id=proj.id,
        user_id=1,
        rag_context="retrieved doc text",
        output_schema={"type": "object"},
    )

    order = [line for line in result.final.split("\n") if line.startswith("## ")]
    assert order == [
        "## System",
        "## Persona",
        "## Project Context",
        "## Memory",
        "## Retrieved Context",
        "## Task",
        "## Output Format",
    ]


# ------------------------------------------------------------ persona
def test_build_includes_persona_by_name(env):
    _make_task(env)
    p = env["persona_engine"].create("Reviewer", "d", "You are a strict reviewer.")

    result = env["builder"].build("q", "ask", persona="Reviewer")
    assert result.persona == "You are a strict reviewer."
    assert result.persona_id == p.id


def test_build_includes_persona_by_id(env):
    _make_task(env)
    p = env["persona_engine"].create("Reviewer", "d", "You are a strict reviewer.")

    result = env["builder"].build("q", "ask", persona=p.id)
    assert result.persona == "You are a strict reviewer."


def test_build_raises_for_unknown_persona(env):
    _make_task(env)
    with pytest.raises(ValueError):
        env["builder"].build("q", "ask", persona="Does Not Exist")


def test_build_no_persona_given_leaves_persona_id_none(env):
    _make_task(env)
    result = env["builder"].build("q", "ask")
    assert result.persona_id is None
    assert result.persona == ""


# ------------------------------------------------------------ project context
def test_build_project_context_joins_description_and_instructions(env):
    _make_task(env)
    proj = env["Project"](user_id=1, description="About widgets.", instructions="Be concise.")
    env["db"].add(proj)
    env["db"].commit()

    result = env["builder"].build("q", "ask", project_id=proj.id, user_id=1)
    assert result.project_context == "About widgets.\nBe concise."


def test_build_skips_project_context_when_user_id_missing(env):
    _make_task(env)
    proj = env["Project"](user_id=1, description="About widgets.", instructions="Be concise.")
    env["db"].add(proj)
    env["db"].commit()

    result = env["builder"].build("q", "ask", project_id=proj.id)  # no user_id
    assert result.project_context == ""


def test_build_missing_project_leaves_empty_context_without_raising(env):
    _make_task(env)
    result = env["builder"].build("q", "ask", project_id=999999, user_id=1)
    assert result.project_context == ""


# ------------------------------------------------------------ memory
def test_build_includes_relevant_memories(env):
    _make_task(env)
    env["db"].add(env["Memory"](user_id=1, fact="prefers concise answers"))
    env["db"].commit()

    result = env["builder"].build("q", "ask", user_id=1)
    assert "prefers concise answers" in result.memory


def test_build_no_user_id_skips_memory_entirely(env):
    _make_task(env)
    env["db"].add(env["Memory"](user_id=1, fact="prefers concise answers"))
    env["db"].commit()

    result = env["builder"].build("q", "ask")  # no user_id
    assert result.memory == ""


# ------------------------------------------------------------ RAG (security: separate section)
def test_build_includes_rag_context_as_its_own_section(env):
    _make_task(env)
    result = env["builder"].build("q", "ask", rag_context="Widgets are efficient.")
    assert result.rag == "Widgets are efficient."
    assert "## Retrieved Context\nWidgets are efficient." in result.final


def test_build_rag_context_is_not_merged_into_task_text_when_template_doesnt_reference_it(env):
    # A task template that only references {{ query }} never sees
    # rag_context injected into it — rag_context only reaches the Task
    # section's rendering when the template itself asks for {{ text }}
    # (see test_build_maps_rag_context_to_text_for_document_body_templates
    # below for that intentional, opposite case).
    _make_task(env)
    result = env["builder"].build("q", "ask", rag_context="SECRET_RAG_MARKER")
    assert "SECRET_RAG_MARKER" not in result.task


def test_build_maps_rag_context_to_text_for_document_body_templates(env):
    # Deliberate: paper_analysis/extract_metadata-style templates use
    # {{ text }} to mean "the document being analyzed" — when rag_context
    # is supplied, it fills that slot (not user_query), so the template's
    # own "Paper text:"-style label shows the real document, not the
    # short query. rag_context still also gets its own Retrieved Context
    # section regardless (checked separately below).
    _make_task(env, template="Paper text: {{ text }}")
    result = env["builder"].build("summarize this", "ask", rag_context="THE ACTUAL PAPER CONTENT")
    assert result.task == "Paper text: THE ACTUAL PAPER CONTENT"
    assert "## Retrieved Context\nTHE ACTUAL PAPER CONTENT" in result.final


def test_build_falls_back_to_user_query_for_text_when_no_rag_context(env):
    _make_task(env, template="{{ text }}")
    result = env["builder"].build("hello", "ask")  # no rag_context
    assert result.task == "hello"


def test_build_supplies_max_chars_as_len_of_rag_context(env):
    _make_task(env, template="first {{ max_chars }} chars: {{ text }}")
    result = env["builder"].build("q", "ask", rag_context="12345")
    assert result.task == "first 5 chars: 12345"


def test_build_metadata_none_values_render_as_empty_not_literal_none(env):
    _make_task(env, template="Title: {{ title }}")
    result = env["builder"].build("q", "ask", metadata={"title": None})
    assert result.task == "Title: "


# ------------------------------------------------------------ output schema
def test_build_includes_output_schema_instruction(env):
    _make_task(env)
    result = env["builder"].build("q", "ask", output_schema={"type": "object", "properties": {}})
    assert "Respond ONLY with JSON" in result.output_schema
    assert '"type": "object"' in result.output_schema


def test_build_no_output_schema_omits_section(env):
    _make_task(env)
    result = env["builder"].build("q", "ask")
    assert result.output_schema == ""


# ------------------------------------------------------------ variable mapping
def test_build_maps_user_query_to_query_question_and_text(env):
    _make_task(env, name="uses_query", template="{{ query }}")
    _make_task(env, name="uses_question", template="{{ question }}")
    _make_task(env, name="uses_text", template="{{ text }}")

    assert env["builder"].build("hello", "uses_query").task == "hello"
    assert env["builder"].build("hello", "uses_question").task == "hello"
    assert env["builder"].build("hello", "uses_text").task == "hello"


# ------------------------------------------------------------ prompt_version_id
def test_build_returns_the_resolved_prompt_version_id(env):
    row_result = env["registry"].create_prompt("ask", "d", "{{ query }}", status="active")
    result = env["builder"].build("q", "ask")
    assert result.prompt_version_id == row_result.id


def test_build_raises_for_unknown_task_name(env):
    with pytest.raises(ValueError):
        env["builder"].build("q", "no-such-task")


# ------------------------------------------------------------ security: Jinja2 variable substitution
def test_security_user_query_containing_jinja_syntax_is_not_evaluated(env):
    _make_task(env, template="Q: {{ query }}")
    result = env["builder"].build("{{ 7 * 7 }}", "ask")
    # If Jinja2 re-parsed the substituted value as template syntax this
    # would render "Q: 49" — it must not: the value is inert literal text.
    assert result.task == "Q: {{ 7 * 7 }}"
    assert "49" not in result.task


# ------------------------------------------------------------ domain injection
def _make_domain_module(env, prompt_name, template):
    env["registry"].create_prompt(prompt_name, "test domain module", template, status="active")


def test_build_with_medical_domain(env):
    _make_task(env, template="CORE: {{ query }}")
    _make_domain_module(env, "domain_medical", "MEDICAL SECTIONS: {{ query }}")

    result = env["builder"].build("a randomized clinical trial", "ask", domain="medical")

    assert result.task == "CORE: a randomized clinical trial\n\nMEDICAL SECTIONS: a randomized clinical trial"
    assert result.domain == "medical"
    assert result.domain_version_id is not None


def test_build_with_general_domain(env):
    _make_task(env, template="CORE: {{ query }}")
    # No domain module seeded at all — "general" never has one:
    # DomainRegistry maps it to "paper_analysis" (the core task itself),
    # not a separate module, and build() skips the fetch entirely for
    # domain == "general" regardless.
    result = env["builder"].build("nothing domain-specific here", "ask", domain="general")

    assert result.task == "CORE: nothing domain-specific here"
    assert result.domain == "general"
    assert result.domain_version_id is None


def test_build_with_domain_override(env):
    _make_task(env, template="CORE: {{ query }}")
    _make_domain_module(env, "domain_medical", "MEDICAL: {{ query }}")
    _make_domain_module(env, "domain_ai_ml", "AI_ML: {{ query }}")

    # Content reads AI/ML-ish, but an explicit domain override still wins
    # — highest priority in DomainRegistry.detect_domain()'s own order.
    result = env["builder"].build("a neural network benchmark", "ask", domain="medical")

    assert "MEDICAL:" in result.task
    assert "AI_ML:" not in result.task
    assert result.domain == "medical"


def test_build_with_domain_detection(env):
    _make_task(env, template="CORE: {{ query }}")
    _make_domain_module(env, "domain_medical", "MEDICAL: {{ query }}")

    # No domain given at all — auto-detected from content via keyword match.
    result = env["builder"].build("This randomized clinical trial enrolled patients at a hospital.", "ask")

    assert result.domain == "medical"
    assert "MEDICAL:" in result.task


# ------------------------------------------------------------ document_type
def test_build_with_explicit_document_type(env):
    _make_task(env, template="CORE: {{ query }}")
    _make_domain_module(env, "domain_medical", "Type: {{ document_type }}")

    result = env["builder"].build("irrelevant content", "ask", domain="medical", document_type="review")

    assert result.document_type == "review"
    assert "Type: review" in result.task


def test_build_auto_detects_document_type_when_not_given(env):
    _make_task(env, template="CORE: {{ query }}")
    _make_domain_module(env, "domain_medical", "Type: {{ document_type }}")

    result = env["builder"].build(
        "This practical guide explains step by step how to proceed.", "ask", domain="medical"
    )

    assert result.document_type == "clinical_guide"
    assert "Type: clinical_guide" in result.task


def test_build_document_type_available_to_any_template_not_just_domain_modules(env):
    _make_task(env, template="CORE for a {{ document_type }} document: {{ query }}")

    result = env["builder"].build("nothing domain-specific here", "ask", document_type="review")

    assert "CORE for a review document" in result.task


def test_build_document_type_defaults_to_general_with_no_signal(env):
    _make_task(env, template="CORE: {{ query }}")

    result = env["builder"].build("Nothing relevant to any known type here.", "ask")

    assert result.document_type == "general"


def test_build_domain_missing_gracefully_falls_back_to_core_only(env):
    _make_task(env, template="CORE: {{ query }}")
    # domain_medical is NOT seeded in this test at all.
    result = env["builder"].build("q", "ask", domain="medical")

    assert result.task == "CORE: q"  # unchanged — no crash, no partial/broken text
    assert result.domain == "medical"  # still records what was requested/detected
    assert result.domain_version_id is None  # but nothing was actually appended


def test_get_available_domains_returns_enabled_domain_names(env):
    domains = env["builder"].get_available_domains()
    assert "medical" in domains
    assert "general" in domains
    assert len(domains) == 9


# ------------------------------------------------------------ preview()
def test_preview_returns_same_result_as_build(env):
    _make_task(env)
    built = env["builder"].build("q", "ask")
    previewed = env["builder"].preview("q", "ask")
    assert built == previewed


def test_preview_also_applies_domain_injection(env):
    _make_task(env, template="CORE: {{ query }}")
    _make_domain_module(env, "domain_medical", "MEDICAL: {{ query }}")

    result = env["builder"].preview("q", "ask", domain="medical")

    assert "MEDICAL:" in result.task
    assert result.domain == "medical"


# ------------------------------------------------------------ Phase A: build_chat_instructions
def test_build_chat_instructions_flat_parity_no_section_headers(env):
    from backend.ai.prompt_builder import CHAT_SYSTEM_FALLBACK

    now = datetime(2026, 7, 26, 15, 30)
    result = env["builder"].build_chat_instructions(
        user_id=1,
        user_name="Ada Lovelace",
        custom_instructions="Be brief.",
        memory_enabled=False,
        now=now,
    )
    assert "## " not in result.final
    assert CHAT_SYSTEM_FALLBACK in result.final or result.final.startswith(CHAT_SYSTEM_FALLBACK[:20])
    assert "The user's name is Ada Lovelace." in result.final
    assert "Current date/time: 2026-07-26 15:30." in result.final
    assert "The user's custom instructions (always follow):\nBe brief." in result.final
    assert result.rag == ""
    assert result.task == ""
    assert "Global system prompt text." not in result.final


def test_build_chat_instructions_uses_chat_system_registry(env):
    env["registry"].create_prompt("chat_system", "test", "Custom chat opening.", status="active")
    result = env["builder"].build_chat_instructions(
        user_id=1, user_name="Ada", memory_enabled=False
    )
    assert result.final.startswith("Custom chat opening.")
    assert result.system == "Custom chat opening."


def test_build_chat_instructions_all_memories_not_top5(env):
    db = env["db"]
    Memory = env["Memory"]
    for i in range(8):
        db.add(Memory(user_id=7, project_id=None, fact=f"global-fact-{i}", importance=1))
    db.commit()
    result = env["builder"].build_chat_instructions(user_id=7, user_name="U", memory_enabled=True)
    for i in range(8):
        assert f"global-fact-{i}" in result.final
    assert "Things you remember about the user:" in result.final


def test_build_chat_instructions_project_ownership(env):
    db = env["db"]
    Project = env["Project"]
    own = Project(user_id=1, name="Mine", instructions="Do science.")
    other = Project(user_id=2, name="Theirs", instructions="Secret.")
    db.add_all([own, other])
    db.commit()

    ok = env["builder"].build_chat_instructions(
        user_id=1, user_name="Ada", project_id=own.id, memory_enabled=False
    )
    assert 'Current project: "Mine".' in ok.final
    assert "Project instructions from the user:\nDo science." in ok.final

    blocked = env["builder"].build_chat_instructions(
        user_id=1, user_name="Ada", project_id=other.id, memory_enabled=False
    )
    assert "Theirs" not in blocked.final
    assert "Secret" not in blocked.final


def test_build_paper_chat_instructions_parity_with_legacy(env):
    from datetime import datetime

    from backend.ai_core.prompts.legacy_paper_chat import render_legacy_paper_chat_prompt
    from backend.ai_core.versions import LEGACY_PAPER_CHAT_PROMPT_VERSION

    now = datetime(2026, 7, 26, 15, 30, 0)
    legacy = render_legacy_paper_chat_prompt(
        user_name="Ada",
        paper_title="CRP and Inflammation",
        authors="Smith et al.",
        year=2024,
        venue="Nature Med",
        now=now,
    )
    assembled = env["builder"].build_paper_chat_instructions(
        user_name="Ada",
        paper_title="CRP and Inflammation",
        authors="Smith et al.",
        year=2024,
        venue="Nature Med",
        now=now,
    )
    assert assembled.final == legacy
    assert assembled.system == legacy
    assert assembled.rag == ""
    assert assembled.document_type == LEGACY_PAPER_CHAT_PROMPT_VERSION


def test_build_paper_chat_instructions_phase1_on_rag_not_final(env):
    from datetime import datetime

    from backend.ai_core.prompts.legacy_paper_chat import render_legacy_paper_chat_prompt

    now = datetime(2026, 7, 26, 15, 30, 0)
    phase1 = "=== Phase 1 Structured Analysis ===\n## Classification\n- domain: medical"
    assembled = env["builder"].build_paper_chat_instructions(
        user_name="Ada",
        paper_title="Paper",
        phase1_context=phase1,
        now=now,
    )
    legacy = render_legacy_paper_chat_prompt(
        user_name="Ada", paper_title="Paper", now=now
    )
    assert assembled.final == legacy
    assert phase1 not in assembled.final
    assert assembled.rag == phase1


def test_build_rejects_foreign_project_context_when_user_id_set(env):
    db = env["db"]
    Project = env["Project"]
    _make_task(env)
    foreign = Project(user_id=99, name="X", description="leak", instructions="nope")
    db.add(foreign)
    db.commit()
    result = env["builder"].build("q", "ask", project_id=foreign.id, user_id=1)
    assert result.project_context == ""
