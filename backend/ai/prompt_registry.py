"""Versioned prompt templates with Jinja2 rendering, over the real
prompt_versions table (migration 0005, extended by migration 0015 — see
docs/prompt-engine-architecture.md §3) — see backend/ai/models.py's
module docstring for why there's no separate PromptTemplate table: 0005
defines one flat table, versions grouped by a plain `name` column, with
`is_active` marking the current one per name.

That means create_prompt() below returns a PromptVersion (the first
version row), not a PromptTemplate — there is no PromptTemplate class to
return. Same resolution already agreed for backend/ai/models.py, applied
here for consistency.

Owns a private declarative Base, distinct from server.py's own Base, so
__init__ only needs the injected Session (per spec) and not a second
"which mapped class" argument. This works because the class maps onto
the real prompt_versions table by name, not by Base identity —
SQLAlchemy classes from different registries can coexist against the
same underlying tables as long as you don't need relationships across
them. This module's own Base now also hosts Persona (backend/ai/
persona_engine.py's model class, not exposed as a PersonaRegistry-style
API here) — added here rather than its own private Base specifically so
a future prompt_executions row can carry a real ForeignKey to both
tables at once (see docs/prompt-engine-architecture.md §2). It does NOT
create either table — that's server.py's/migrations' job; this assumes
they already exist.

Lifecycle state machine (migration 0015): a version's `status` is one of
draft|active|archived. A row may only have `is_active=True` if its own
`status == 'active'` — enforced here (create_prompt/add_version), not
just documented, since is_active is what get_active_version()/get_prompt()
actually key off of. `status='draft'` is the default everywhere a caller
doesn't say otherwise: a newly created prompt is NOT automatically
servable via get_prompt() until something (a caller passing
status="active", or a later activate_prompt() call) makes it active.
This is a deliberate behavior change from before this migration (the
first version used to always be immediately active) — every real caller
that needs "create and immediately serve" now says so explicitly via
status="active" (see backend/ai/prompts.py's ensure_prompt(),
backend/ai/seed.py's seed_prompts()).
"""
import json
from typing import Optional, List

from jinja2.sandbox import SandboxedEnvironment
from jinja2.exceptions import TemplateError as Jinja2TemplateError
from sqlalchemy.orm import Session, declarative_base

from .models import (
    create_prompt_version_model, create_persona_model, create_prompt_execution_model,
)

_Base = declarative_base()
PromptVersion = create_prompt_version_model(_Base)
# Persona and PromptExecution live on this same private Base (not their
# own) specifically so PromptExecution.prompt_version_id/persona_id can
# carry real SQLAlchemy ForeignKeys — FKs only resolve within one shared
# MetaData (see docs/prompt-engine-architecture.md §2/§9). This also
# means server.py's existing `_ai_prompt_base.metadata.create_all(engine,
# checkfirst=True)` bootstrap picks up both tables automatically, no
# server.py change needed for that.
Persona = create_persona_model(_Base)
PromptExecution = create_prompt_execution_model(_Base)

# Shared, module-level — constructing a jinja2.Environment is real setup
# work (parses/compiles internal helper templates), so one reused
# instance across every get_prompt() call, not a fresh Environment per
# call. SandboxedEnvironment, not a bare Template: it restricts dangerous
# attribute/method access during rendering (the `{{ ''.__class__.
# __mro__[1].__subclasses__() }}`-style SSTI escape route some SSTI
# advisories rely on), with zero effect on any normal template's output
# — every real template in this app is plain `{{ var }}` substitution,
# which sandboxing doesn't touch at all. Deliberately NOT
# autoescape=True: see PromptBuilder's module docstring for why
# HTML-entity-escaping a plain-text LLM prompt would corrupt legitimate
# academic content ("&"/"<"/">" in real papers) for no protection
# against the injection class that actually matters here.
_jinja_env = SandboxedEnvironment()


class TemplateError(Exception):
    """Wraps any Jinja2 parse/render failure — callers only need to
    catch this module's own exception type, not jinja2's."""


class PromptRegistry:
    def __init__(self, db_session: Session):
        self.db = db_session

    # ------------------------------------------------------------ reads
    def get_active_version(self, name: str) -> Optional[PromptVersion]:
        return (
            self.db.query(PromptVersion)
            .filter_by(name=name, is_active=True)
            .first()
        )

    def list_prompts(self) -> List[PromptVersion]:
        """Every version of every prompt — the full registry inventory,
        not filtered to what's currently active (that's
        get_active_prompts() now). Changed from the original "one active
        row per name" behavior specifically so an authoring/admin view can
        see draft and archived versions too, not just what's being served."""
        return self.db.query(PromptVersion).all()

    def get_prompts_by_category(self, category: str) -> List[PromptVersion]:
        """All versions tagged with this category, any status — category
        is an orthogonal grouping label, not a lifecycle filter (see
        docs/prompt-engine-architecture.md §3.1 on why it's decoupled
        from `name`)."""
        return self.db.query(PromptVersion).filter_by(category=category).all()

    def get_active_prompts(self) -> List[PromptVersion]:
        """Every row with status='active' — NOT the same as "every row
        with is_active=True". A name can have more than one status='active'
        version in its history (e.g. a previously-active version that
        hasn't been explicitly archived yet); is_active narrows that down
        to "the one currently served," this doesn't."""
        return self.db.query(PromptVersion).filter_by(status="active").all()

    def get_prompts_by_status(self, status: str) -> List[PromptVersion]:
        return self.db.query(PromptVersion).filter_by(status=status).all()

    def get_prompt(self, name: str, version: Optional[int] = None,
                   variables: Optional[dict] = None) -> tuple[str, PromptVersion]:
        """Returns (rendered_text, the PromptVersion row that produced it)
        — callers need the row to attribute an AI call to the exact
        prompt version that produced it (prompt_executions,
        AIUsageLedger.prompt_version_id / CostLedgerEntry.prompt_version_id
        — see docs/prompt-engine-audit.md §3). Breaking change from the
        original str-only return; every caller in this codebase has been
        updated to unpack the tuple."""
        if version is not None:
            row = self.db.query(PromptVersion).filter_by(name=name, version=version).first()
        else:
            row = self.get_active_version(name)

        if not row:
            raise ValueError(
                f"prompt not found: name={name!r}"
                + (f" version={version!r}" if version is not None else " (no active version)")
            )

        try:
            rendered = _jinja_env.from_string(row.template).render(**(variables or {}))
        except Jinja2TemplateError as exc:
            raise TemplateError(
                f"failed to render prompt {name!r} v{row.version}: {exc}") from exc
        return rendered, row

    # ------------------------------------------------------------ writes
    def create_prompt(
        self, name: str, description: str, template_text: str,
        default_version: int = 1, *,
        status: str = "draft", category: str = "",
        examples: Optional[list] = None, expected_output_type: str = "text",
        author_user_id: Optional[int] = None,
    ) -> PromptVersion:
        """First version of a new name. `is_active` is derived from
        `status`, not an independent parameter — a version can only be
        the one served for its name if it's actually status='active'
        (see module docstring). Pass status="active" for a prompt that
        should be immediately servable; the default ("draft") is not."""
        existing = (
            self.db.query(PromptVersion)
            .filter_by(name=name, version=default_version)
            .first()
        )
        if existing:
            raise ValueError(f"prompt {name!r} version {default_version} already exists")

        row = PromptVersion(
            name=name, version=default_version, template=template_text,
            is_active=(status == "active"),
            description=description, status=status, category=category,
            examples=json.dumps(examples if examples is not None else []),
            expected_output_type=expected_output_type, author_user_id=author_user_id,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def add_version(
        self, name: str, template_text: str, is_active: bool = False, *,
        status: str = "draft", description: str = "", category: str = "",
        examples: Optional[list] = None, expected_output_type: str = "text",
        author_user_id: Optional[int] = None,
    ) -> PromptVersion:
        if is_active and status != "active":
            raise ValueError(
                f"cannot create a version with is_active=True and status={status!r} — "
                "only a status='active' version may be the one served (activate_prompt() "
                "or pass status=\"active\" explicitly)"
            )

        existing_versions = (
            self.db.query(PromptVersion).filter_by(name=name).all()
        )
        if not existing_versions:
            raise ValueError(f"no prompt named {name!r} — use create_prompt() first")

        next_version = max(v.version for v in existing_versions) + 1

        if is_active:
            for v in existing_versions:
                v.is_active = False

        row = PromptVersion(
            name=name, version=next_version, template=template_text, is_active=is_active,
            status=status, description=description, category=category,
            examples=json.dumps(examples if examples is not None else []),
            expected_output_type=expected_output_type, author_user_id=author_user_id,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def archive_prompt(self, name: str) -> PromptVersion:
        """Archives the currently active version for `name` — sets
        status='archived' and clears is_active (an archived version can
        never be the one served, per the state machine). Operates on the
        active row specifically, not every historical version: retiring
        the live prompt is the common case this exists for; archiving a
        whole name's full history is a different operation this doesn't
        attempt."""
        row = self.get_active_version(name)
        if not row:
            raise ValueError(f"no active version to archive for {name!r}")
        row.status = "archived"
        row.is_active = False
        self.db.commit()
        return row

    def activate_prompt(self, name: str) -> PromptVersion:
        """Activates the latest (highest version number) row for `name`
        — sets status='active' and is_active=True, deactivating every
        other version, same invariant add_version(is_active=True)
        enforces. Always the latest version, not a caller-chosen one —
        this method has no version parameter; pin a specific version via
        add_version(..., is_active=True, status="active") instead if the
        version to activate isn't the newest one."""
        versions = self.db.query(PromptVersion).filter_by(name=name).all()
        if not versions:
            raise ValueError(f"no prompt named {name!r}")
        latest = max(versions, key=lambda v: v.version)
        for v in versions:
            v.is_active = False
        latest.status = "active"
        latest.is_active = True
        self.db.commit()
        return latest
