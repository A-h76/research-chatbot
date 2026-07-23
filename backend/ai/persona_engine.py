"""PersonaEngine — CRUD over the personas table (migrations/0015_prompt_engine.sql,
docs/prompt-engine-architecture.md §5).

Constructor-injected (db_session, Persona) — same reason as every other
module in backend/ai/auth/quotas: never `import server`. `Persona` itself
lives on backend/ai/prompt_registry.py's private Base, not a Base of its
own (see that module's docstring for why: a future prompt_executions row
needs a real FK to both prompt_versions and personas at once, which only
works if both are registered against the same MetaData).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    # Static-analysis only — see backend/ai/memory_engine.py's identical
    # comment for why this doesn't violate the "never import server at
    # runtime" rule (n/a here — Persona lives on prompt_registry.py's own
    # Base, not server.py's, but the same TYPE_CHECKING-erasure reasoning
    # applies to keeping this constructor-injected class out of the real
    # import graph).
    from backend.ai.prompt_registry import Persona


class PersonaEngine:
    def __init__(self, db_session, Persona):
        self.db = db_session
        self.Persona = Persona

    # ------------------------------------------------------------ reads
    def list_active(self) -> List[Persona]:
        return self.db.query(self.Persona).filter_by(is_active=True).all()

    def get(self, persona_id: int) -> Optional[Persona]:
        return self.db.get(self.Persona, persona_id)

    def get_by_name(self, name: str) -> Optional[Persona]:
        return self.db.query(self.Persona).filter_by(name=name).first()

    # ------------------------------------------------------------ writes
    def create(self, name: str, description: str, system_prompt: str) -> Persona:
        if self.get_by_name(name) is not None:
            raise ValueError(f"persona {name!r} already exists")
        row = self.Persona(
            name=name,
            description=description,
            system_prompt=system_prompt,
            is_active=True,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def update(self, persona_id: int, **fields) -> Persona:
        row = self.get(persona_id)
        if not row:
            raise ValueError(f"no persona with id={persona_id}")
        for key, value in fields.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return row

    def deactivate(self, persona_id: int) -> Persona:
        return self.update(persona_id, is_active=False)
