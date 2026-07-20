"""Versioned prompt templates with Jinja2 rendering, over the real
prompt_versions table (migration 0005) — see backend/ai/models.py's
module docstring for why there's no separate PromptTemplate table: 0005
defines one flat table, versions grouped by a plain `name` column, with
`is_active` marking the current one per name.

That means create_prompt() below returns a PromptVersion (the first
version row), not a PromptTemplate — there is no PromptTemplate class to
return. Same resolution already agreed for backend/ai/models.py, applied
here for consistency.

Owns a private declarative Base just for PromptVersion, distinct from
server.py's real one, so __init__ only needs the injected Session (per
spec) and not a second "which mapped class" parameter. This works
because the class maps onto the real prompt_versions table by name, not
by Base identity — SQLAlchemy classes from different registries can
coexist against the same underlying tables as long as you don't need
relationships across them, and this registry only ever touches
prompt_versions on its own. It does NOT create the table — that's
server.py's/migrations' job; this assumes it already exists.
"""
from typing import Optional, List

from jinja2 import Template
from jinja2.exceptions import TemplateError as Jinja2TemplateError
from sqlalchemy.orm import Session, declarative_base

from .models import create_prompt_version_model

_Base = declarative_base()
PromptVersion = create_prompt_version_model(_Base)


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
        """One row per distinct name — its currently active version, not
        every historical version. That's what "list all prompts" means
        to a caller who wants to know what's currently available to
        render, not the full version history of each."""
        return self.db.query(PromptVersion).filter_by(is_active=True).all()

    def get_prompt(self, name: str, version: Optional[int] = None,
                   variables: Optional[dict] = None) -> str:
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
            return Template(row.template).render(**(variables or {}))
        except Jinja2TemplateError as exc:
            raise TemplateError(
                f"failed to render prompt {name!r} v{row.version}: {exc}") from exc

    # ------------------------------------------------------------ writes
    def create_prompt(self, name: str, description: str, template_text: str,
                      default_version: int = 1) -> PromptVersion:
        """`description` isn't persisted — prompt_versions has no such
        column (see module docstring) — it's accepted so this method's
        signature matches the spec, not silently dropped without a
        reason to point back to."""
        existing = (
            self.db.query(PromptVersion)
            .filter_by(name=name, version=default_version)
            .first()
        )
        if existing:
            raise ValueError(f"prompt {name!r} version {default_version} already exists")

        row = PromptVersion(name=name, version=default_version,
                            template=template_text, is_active=True)
        self.db.add(row)
        self.db.commit()
        return row

    def add_version(self, name: str, template_text: str,
                    is_active: bool = False) -> PromptVersion:
        existing_versions = (
            self.db.query(PromptVersion).filter_by(name=name).all()
        )
        if not existing_versions:
            raise ValueError(f"no prompt named {name!r} — use create_prompt() first")

        next_version = max(v.version for v in existing_versions) + 1

        if is_active:
            for v in existing_versions:
                v.is_active = False

        row = PromptVersion(name=name, version=next_version,
                            template=template_text, is_active=is_active)
        self.db.add(row)
        self.db.commit()
        return row
