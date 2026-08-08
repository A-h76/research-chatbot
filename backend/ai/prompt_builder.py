"""PromptBuilder — assembles the layered prompt (System -> Persona ->
Project Context -> Memory -> RAG -> Task [+ Domain] -> Output Schema)
described in docs/prompt-engine-architecture.md Section 8, wiring
together every other prompt-engine piece: SystemPromptManager,
PersonaEngine, MemoryEngine, PromptRegistry, DomainRegistry.
Deliberately does NOT take a ModelRegistry/ModelRouter — this class's
job stops at "produce the text to send"; calling a model with that text
is the caller's job (see preview()'s docstring for what that means for
the build()/preview() distinction here).

Phase A also exposes build_chat_instructions() — a dedicated chat
parity path (chat_system only, flat output, all memories, project
ownership) used by /api/chat. That path does NOT use AssembledPrompt.final
section headers and does NOT prepend the global system_prompt.

Paper chat uses build_paper_chat_instructions() — legacy M7 system text
parity via ``render_legacy_paper_chat_prompt``. Optional ``phase1_context``
is returned separately on AssembledPrompt.rag so the route can inject it
as a developer message without changing Stage 1 system-prompt hash parity.

Security notes (mechanics are in build()'s own comments below):

- The system prompt is always the first section in `final` — nothing
  assembled here can be made to precede it just by what a caller passes in.
- Retrieved context (`rag_context`) always gets its own "## Retrieved
  Context" section, unconditionally. It is ADDITIONALLY used to fill a
  Task template's own {{ text }} variable when that template references
  one (paper_analysis, extract_metadata — see build()'s own docstring)
  — this is deliberate, not a leak: those templates exist specifically
  to analyze the one document being passed in as rag_context (it's the
  subject of the task, not incidental supporting material from a
  separate retrieval step), and each such template already wraps {{
  text }} in its own explicit label ("Paper text (first N
  characters):", "**Paper Content:**") — so the model still always sees
  a clear boundary around where retrieved content begins, it just also
  appears where the task's own instructions expect it, instead of being
  silently absent from that slot. Query-style tasks (semantic_search
  and friends) are unaffected: they don't reference {{ text }}, so
  rag_context only ever reaches them via its own section.
- User-supplied text (`user_query`) only ever reaches Jinja2 as a
  **template variable value** passed to PromptRegistry.get_prompt(),
  never as template source. Jinja2 does not re-parse variable values as
  template syntax — a query containing `{{ 7 * 7 }}` or a Jinja2-SSTI
  payload renders as inert literal text, never evaluated. That's the
  real protection Jinja2 gives here, and it's covered by a real test
  (test_prompt_builder.py), not just asserted in a comment.
- PromptRegistry.get_prompt() itself now renders through a Jinja2
  SandboxedEnvironment (backend/ai/prompt_registry.py), not a bare
  Template — restricts dangerous attribute/method access reachable from
  TEMPLATE SOURCE (an admin-authored prompt, in this app's threat
  model), covered by its own test in test_prompt_registry.py.

  Deliberately NOT applied: HTML-style `autoescape=True` output escaping
  on top of either of those. These are plain-text prompts sent to a
  model API, not HTML rendered in a browser — entity-escaping a paper's
  own "&"/"<"/">" characters (routine in real academic text: chemistry
  notation, inequalities, "R&D") would corrupt legitimate content for no
  protection against the injection class that actually matters for LLM
  prompts (prompt injection isn't fixed by any escaping scheme; section
  separation, above, is the real mitigation). Flagging this explicitly
  since "ensure Jinja2 ... is active" could be read as asking for that
  flag specifically — it was considered and rejected (twice now) in
  favor of sandboxing, which gives a real guarantee HTML-escaping
  wouldn't and has zero effect on legitimate output.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Same fallback as historical server._CHAT_SYSTEM_FALLBACK — single source
# so registry misses never fail a chat request.
CHAT_SYSTEM_FALLBACK = (
    "You are Dhund, a helpful assistant specialised in academic "
    "research and thesis writing, but able to help with anything. "
    "Use markdown. Be precise with citations and honest about "
    "uncertainty. When you used web search results or document excerpts, "
    "cite the sources inline."
)


@dataclass
class AssembledPrompt:
    system: str
    persona: str
    project_context: str
    memory: str
    rag: str
    task: str
    output_schema: str
    final: str
    prompt_version_id: Optional[int]
    persona_id: Optional[int]
    domain: Optional[str] = None
    domain_version_id: Optional[int] = None
    document_type: Optional[str] = None


class PromptBuilder:
    def __init__(
        self,
        system_prompt_manager,
        persona_engine,
        memory_engine,
        prompt_registry,
        SessionLocal,
        Project,
        domain_registry,
    ):
        self.system_prompt_manager = system_prompt_manager
        self.persona_engine = persona_engine
        self.memory_engine = memory_engine
        self.prompt_registry = prompt_registry
        self.SessionLocal = SessionLocal
        self.Project = Project
        self.domain_registry = domain_registry

    def build_chat_instructions(
        self,
        *,
        user_id: int,
        user_name: str,
        custom_instructions: str = "",
        project_id: Optional[int] = None,
        memory_enabled: bool = True,
        now: Optional[datetime] = None,
        assistant_mode: Optional[str] = None,
        research_state: Optional[dict] = None,
        assistant_intent: Optional[str] = None,
    ) -> AssembledPrompt:
        """Flat chat system prompt — behavioral parity with legacy
        server.build_system_prompt().

        - Opening from prompt_versions name ``chat_system`` only (not
          global ``system_prompt``).
        - Flat ``\\n\\n``-joined parts (no ``##`` section headers).
        - All global + project memories when memory_enabled (not top-5).
        - Project included only if it exists and ``project.user_id == user_id``.
        - No RAG / domain / task template body in the flat string.
        - Optional Assistant Engine layers (ADR-0018): when ``assistant_mode``
          and/or ``research_state`` are provided, append mode-composed
          decision context after the flat parity body.
        """
        opening, prompt_version_id = self._chat_system_opening()
        when = now or datetime.now()
        parts = [
            opening,
            f"The user's name is {user_name}.",
            f"Current date/time: {when.strftime('%Y-%m-%d %H:%M')}.",
        ]

        if custom_instructions:
            parts.append("The user's custom instructions (always follow):\n" + custom_instructions)

        project_context = ""
        owned_project_id: Optional[int] = None
        if project_id is not None:
            project_context = self._chat_project_context(project_id, user_id)
            if project_context:
                owned_project_id = project_id
                parts.append(project_context)

        memory_text = ""
        if memory_enabled:
            global_mems, _legacy_proj = self.memory_engine.get_chat_memories(
                user_id, project_id=None
            )
            if global_mems:
                block = "Things you remember about the user:\n" + "\n".join(f"- {m}" for m in global_mems)
                parts.append(block)
                memory_text = block

            if owned_project_id is not None:
                research_mem_block = self.build_project_memory_context(
                    user_id=user_id,
                    project_id=owned_project_id,
                    light=False,
                )
                if research_mem_block:
                    parts.append(research_mem_block)
                    memory_text = (
                        f"{memory_text}\n\n{research_mem_block}".strip()
                        if memory_text
                        else research_mem_block
                    )

        assistant_task = ""
        if assistant_mode or research_state is not None:
            from backend.assistant.prompt_layers import compose_assistant_layers

            layers = compose_assistant_layers(
                mode=assistant_mode,
                research_state=research_state,
                intent=assistant_intent,
            )
            if layers:
                parts.append(layers)
                assistant_task = f"assistant_mode:{(assistant_mode or 'research_partner')}"

        flat = "\n\n".join(parts)
        return AssembledPrompt(
            system=opening,
            persona="",
            project_context=project_context,
            memory=memory_text,
            rag="",
            task=assistant_task,
            output_schema="",
            final=flat,
            prompt_version_id=prompt_version_id,
            persona_id=None,
            domain=None,
            domain_version_id=None,
            document_type=None,
        )

    def build_paper_chat_instructions(
        self,
        *,
        user_name: str,
        paper_title: str,
        authors: Optional[str] = None,
        year=None,
        venue: Optional[str] = None,
        phase1_context: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> AssembledPrompt:
        """Paper Chat system instructions — parity with M7 legacy prompt.

        System text is always ``render_legacy_paper_chat_prompt`` (same as
        Stage 1 ``LEGACY_PAPER_CHAT_PROMPT_VERSION``). When ``phase1_context``
        is provided it is stored on ``AssembledPrompt.rag`` for the caller to
        inject as a developer message — it is NOT appended to ``final``, so
        Stage 1 shadow hash parity against the legacy system prompt is
        preserved.
        """
        from backend.ai_core.prompts.legacy_paper_chat import render_legacy_paper_chat_prompt
        from backend.ai_core.versions import LEGACY_PAPER_CHAT_PROMPT_VERSION

        system = render_legacy_paper_chat_prompt(
            user_name=user_name,
            paper_title=paper_title,
            authors=authors,
            year=year,
            venue=venue,
            now=now,
        )
        phase1 = (phase1_context or "").strip()
        return AssembledPrompt(
            system=system,
            persona="",
            project_context="",
            memory="",
            rag=phase1,
            task="",
            output_schema="",
            final=system,
            prompt_version_id=None,
            persona_id=None,
            domain=None,
            domain_version_id=None,
            document_type=LEGACY_PAPER_CHAT_PROMPT_VERSION,
        )

    def build_project_memory_context(
        self,
        *,
        user_id: int,
        project_id: int,
        light: bool = False,
        max_chars: int = 4000,
        kinds: Optional[list] = None,
    ) -> str:
        """Developer-context block of project research memories (Sprint C).

        Never includes chat-extracted memories. light=True for research console.
        """
        rows = self.memory_engine.get_project_memory_context(
            user_id,
            project_id,
            kinds=kinds,
            max_chars=max_chars,
            light=light,
        )
        if not rows:
            return ""
        lines = [
            "=== Project Research Memory (developer context — not user text) ===",
            "Durable findings from prior project research. Prefer these when relevant.",
            "Do not invent memories that are not listed.",
        ]
        for m in rows:
            kind = getattr(m, "kind", None) or "fact"
            pin = " [pinned]" if getattr(m, "pinned", 0) else ""
            lines.append(f"- ({kind}{pin}) {m.fact}")
        return "\n".join(lines)

    def build_project_research(
        self,
        *,
        intent: str,
        query: str,
        papers_json: str,
        memory_context: str = "",
    ) -> str:
        """Project-scoped cross-paper research prompt (Sprint B).

        Renders the versioned ``project_research`` template from PromptRegistry.
        ProjectResearchService supplies data; PromptBuilder owns composition.
        Optional light memory_context is prepended as developer context.
        """
        from backend.projects.prompts import INTENT_LABELS, PROJECT_RESEARCH_PROMPT
        from jinja2.sandbox import SandboxedEnvironment

        variables = {
            "intent_label": INTENT_LABELS.get(intent, intent),
            "query": (query or "").strip(),
            "papers_json": papers_json,
        }
        try:
            text, _ = self.prompt_registry.get_prompt("project_research", variables=variables)
        except ValueError:
            env = SandboxedEnvironment()
            text = env.from_string(PROJECT_RESEARCH_PROMPT).render(**variables)
        except Exception:
            logging.getLogger(__name__).warning(
                "project_research prompt fetch failed, using fallback", exc_info=True
            )
            env = SandboxedEnvironment()
            text = env.from_string(PROJECT_RESEARCH_PROMPT).render(**variables)

        mem = (memory_context or "").strip()
        if mem:
            return f"{mem}\n\n{text}"
        return text

    def _chat_system_opening(self) -> tuple[str, Optional[int]]:
        try:
            text, version = self.prompt_registry.get_prompt("chat_system")
            return text, version.id if version is not None else None
        except ValueError:
            return CHAT_SYSTEM_FALLBACK, None
        except Exception:
            logging.getLogger(__name__).warning(
                "chat_system prompt fetch failed, using fallback", exc_info=True
            )
            return CHAT_SYSTEM_FALLBACK, None

    def _chat_project_context(self, project_id: int, user_id: int) -> str:
        if user_id is None:
            return ""
        db = self.SessionLocal()
        try:
            project = db.get(self.Project, project_id)
            if project is None:
                return ""
            owner_id = getattr(project, "user_id", None)
            # Fail closed: require an owning user_id that matches the caller.
            if owner_id is None or int(owner_id) != int(user_id):
                return ""
            chunks = [f'Current project: "{getattr(project, "name", "") or ""}".']
            instructions = getattr(project, "instructions", None) or ""
            if instructions:
                chunks.append("Project instructions from the user:\n" + instructions)
            return "\n\n".join(chunks)
        finally:
            db.close()

    def build(
        self,
        user_query: str,
        task_name: str = "paper_analysis",
        persona=None,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        rag_context: Optional[str] = None,
        output_schema: Optional[dict] = None,
        domain: Optional[str] = None,
        metadata: Optional[dict] = None,
        document_type: Optional[str] = None,
        phase1_context: Optional[str] = None,
    ) -> AssembledPrompt:
        """`persona` may be a name (str) or an id (int). Raises ValueError
        if a persona is given but doesn't resolve to a real row — a typo
        here should fail loudly, not silently assemble a prompt with a
        different personality than the caller asked for. A missing
        `project_id` (project since deleted, etc.) does NOT raise — it
        just leaves Project Context empty, since a stale project
        shouldn't hard-fail an otherwise-valid request the way a bad
        persona name (closer to a caller bug) should.

        Project Context: when ``user_id`` is provided, the project is only
        injected if ``project.user_id`` matches (ownership guard).
        """
        system = self.system_prompt_manager.get_active_prompt()

        persona_row = None
        if persona is not None:
            persona_row = (
                self.persona_engine.get_by_name(persona)
                if isinstance(persona, str)
                else self.persona_engine.get(persona)
            )
            if persona_row is None:
                raise ValueError(f"no such persona: {persona!r}")
        persona_text = persona_row.system_prompt if persona_row else ""

        project_context = ""
        if project_id is not None:
            db = self.SessionLocal()
            try:
                project = db.get(self.Project, project_id)
                # Phase 3 / F3.2: never inject another user's project (or any
                # project) when user_id is missing — fail closed.
                if project is not None and user_id is not None:
                    owner_id = getattr(project, "user_id", None)
                    if owner_id is not None and int(owner_id) == int(user_id):
                        project_context = "\n".join(
                            s for s in (project.description, project.instructions) if s
                        )
            finally:
                db.close()

        memory_text = ""
        if user_id is not None:
            memories = self.memory_engine.get_relevant_memories(user_id, user_query, project_id=project_id)
            memory_text = "\n".join(f"- {m.fact}" for m in memories)

        rag_text = rag_context or ""
        if phase1_context:
            rag_text = f"{phase1_context}\n\n{rag_text}" if rag_text else phase1_context

        if document_type is None:
            document_type = self.domain_registry.detect_document_type(
                content=rag_context or user_query, metadata=metadata or {}
            )

        render_variables = {
            "query": user_query,
            "question": user_query,
            "text": rag_context if rag_context else user_query,
            "max_chars": len(rag_context) if rag_context else "",
            "title": (metadata or {}).get("title") or "",
            "authors": (metadata or {}).get("authors") or "",
            "year": (metadata or {}).get("year") or "",
            "venue": (metadata or {}).get("venue") or "",
            "document_type": document_type,
        }
        task_text, prompt_version = self.prompt_registry.get_prompt(task_name, variables=render_variables)

        if domain is None:
            domain = self.domain_registry.detect_domain(metadata=metadata or {}, content=rag_context or user_query)

        domain_version_id = None
        if domain != "general":
            domain_prompt_name = self.domain_registry.get_domain_prompt_name(domain)
            if domain_prompt_name:
                try:
                    domain_text, domain_version = self.prompt_registry.get_prompt(
                        domain_prompt_name, variables=render_variables
                    )
                    task_text = f"{task_text}\n\n{domain_text}"
                    domain_version_id = domain_version.id
                except ValueError:
                    pass

        schema_text = ""
        if output_schema:
            schema_text = "Respond ONLY with JSON matching this schema:\n" + json.dumps(output_schema, indent=2)

        sections = [
            ("System", system),
            ("Persona", persona_text),
            ("Project Context", project_context),
            ("Memory", memory_text),
            ("Retrieved Context", rag_text),
            ("Task", task_text),
            ("Output Format", schema_text),
        ]
        final = "\n\n".join(f"## {label}\n{body}" for label, body in sections if body)

        return AssembledPrompt(
            system=system,
            persona=persona_text,
            project_context=project_context,
            memory=memory_text,
            rag=rag_text,
            task=task_text,
            output_schema=schema_text,
            final=final,
            prompt_version_id=prompt_version.id,
            persona_id=persona_row.id if persona_row else None,
            domain=domain,
            domain_version_id=domain_version_id,
            document_type=document_type,
        )

    def preview(self, *args, **kwargs) -> AssembledPrompt:
        """Identical to build() today — see module docstring."""
        return self.build(*args, **kwargs)

    def get_available_domains(self):
        """Enabled domain names only — same rule DomainRegistry.detect_domain()
        itself already applies (never route toward a disabled domain)."""
        return [d["name"] for d in self.domain_registry.list_domains(enabled_only=True)]
