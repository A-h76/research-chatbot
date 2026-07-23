"""PromptBuilder — assembles the layered prompt (System -> Persona ->
Project Context -> Memory -> RAG -> Task [+ Domain] -> Output Schema)
described in docs/prompt-engine-architecture.md Section 8, wiring
together every other prompt-engine piece: SystemPromptManager,
PersonaEngine, MemoryEngine, PromptRegistry, DomainRegistry.
Deliberately does NOT take a ModelRegistry/ModelRouter — this class's
job stops at "produce the text to send"; calling a model with that text
is the caller's job (see preview()'s docstring for what that means for
the build()/preview() distinction here).

Security notes (mechanics are in build()'s own comments below):

- The system prompt is always the first section in `final` — nothing
  assembled here can be made to precede it just by what a caller passes in.
- Retrieved context (`rag_context`) is always its own section, never
  folded into the Task section's own template variables. A caller can't
  make retrieved document text masquerade as part of the task
  instruction just by how it's passed in.
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
from dataclasses import dataclass
from typing import Optional


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
    ) -> AssembledPrompt:
        """`persona` may be a name (str) or an id (int). Raises ValueError
        if a persona is given but doesn't resolve to a real row — a typo
        here should fail loudly, not silently assemble a prompt with a
        different personality than the caller asked for. A missing
        `project_id` (project since deleted, etc.) does NOT raise — it
        just leaves Project Context empty, since a stale project
        shouldn't hard-fail an otherwise-valid request the way a bad
        persona name (closer to a caller bug) should.

        `metadata` (venue, title, authors, year, ...) feeds two things:
        DomainRegistry's venue-based detection, and — new here — the
        same fields as render variables for both the core task and any
        domain module, since the real paper_analysis/domain_* templates
        already reference {{ title }}/{{ authors }}/{{ year }}/{{ venue }}
        and had nothing supplying them before this parameter existed.

        Domain injection: if `domain` isn't given, DomainRegistry.detect_domain()
        picks one (metadata venue match, then rag_context/user_query
        keyword match, then "general"). "general" and any domain whose
        module prompt isn't found/seeded are skipped gracefully — the
        Task section is then just the core task_name render, unchanged
        from before this parameter existed. When a domain module *is*
        found, its own rendered text is appended after the core task
        text (core_text + "\\n\\n" + domain_text) into a single Task
        section — domain/domain_version_id on the returned AssembledPrompt
        record which one (if any) was used, for audit.

        Known content-shape caveat, not a bug in this method: the
        domain_medical/domain_ai_ml modules seeded so far
        (backend/ai/seed.py) are each a COMPLETE, standalone analysis
        prompt (opening + paper content/metadata + all of their own
        sections, including a repeat of the core 16) — a necessity when
        they were seeded, since PromptRegistry has no template-composition
        mechanism. Appending one of those after an already-rendered core
        task_name prompt (as this method does, per its own spec) will
        currently duplicate the opening/paper-content block and the core
        16 sections rather than cleanly extending them. Fixing that means
        re-authoring DOMAIN_MODULES as extension-only content (sections
        17+, no repeated preamble) — a seed.py content change, out of
        scope for this method, which only builds the injection mechanism.

        Note on the {{ text }} mapping below: some existing templates
        (paper_analysis, extract_metadata) already use {{ text }} to mean
        "the source document", not "the user's query" — routing those
        specific task names through this builder would incorrectly inject
        user_query into that slot instead of real paper text. This
        mapping is for query-style tasks (semantic_search and friends);
        document-body tasks should keep calling
        PromptRegistry.get_prompt() directly with their real variables
        until templates actually converge on `query` everywhere."""
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
                if project:
                    project_context = "\n".join(s for s in (project.description, project.instructions) if s)
            finally:
                db.close()

        memory_text = ""
        if user_id is not None:
            memories = self.memory_engine.get_relevant_memories(user_id, user_query, project_id=project_id)
            memory_text = "\n".join(f"- {m.fact}" for m in memories)

        # Always its own section — never merged into the Task variables
        # below (see module docstring's Security note).
        rag_text = rag_context or ""

        render_variables = {
            "query": user_query,
            "question": user_query,
            "text": user_query,
            "title": (metadata or {}).get("title", ""),
            "authors": (metadata or {}).get("authors", ""),
            "year": (metadata or {}).get("year", ""),
            "venue": (metadata or {}).get("venue", ""),
        }
        task_text, prompt_version = self.prompt_registry.get_prompt(task_name, variables=render_variables)

        # ------------------------------------------------------------ domain
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
                    # Domain module not seeded/found — skip gracefully,
                    # per this method's own spec: a missing domain
                    # module falls back to the core task text as-is,
                    # it doesn't fail the whole build.
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
        )

    def preview(self, *args, **kwargs) -> AssembledPrompt:
        """Identical to build() today, domain injection included: this
        class never calls a model itself (no ModelRegistry/ModelRouter is
        injected — see module docstring), so "does not execute the
        model" is already true of build() too. preview() exists as the
        stable, self-documenting name for a caller that only wants to
        inspect an assembled prompt (an admin "preview this prompt" UI,
        say) without it ever being mistaken for a real call site later —
        the naming signals intent; the code path is the same either way
        because there's nothing here that calls a model to skip."""
        return self.build(*args, **kwargs)

    def get_available_domains(self):
        """Enabled domain names only — same rule DomainRegistry.detect_domain()
        itself already applies (never route toward a disabled domain)."""
        return [d["name"] for d in self.domain_registry.list_domains(enabled_only=True)]
