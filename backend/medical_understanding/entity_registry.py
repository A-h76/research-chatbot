"""Shared entity registry — the one source of truth for every
ClinicalEntity extracted during a single pipeline run, across all eight
extractors. Two jobs: prevent the same real-world concept being
registered twice under slightly different raw text (register_entity's
dedup, keyed by normalized value + type), and help resolve an ambiguous
abbreviation (e.g. "MS") using whatever this same document has already
established elsewhere (resolve_ambiguity) — see normalizers.py's
AMBIGUOUS_ABBREVIATIONS for the known-ambiguous-term data this reads.

Lock-protected: registry.py's ExtractorRegistry.execute_parallel() runs
extractors on a real thread pool, and every extractor is handed this
same EntityRegistry instance to read from AND write to during its own
extract() call (that's the whole point of a *shared* registry — an
extractor started after another has already registered "myocardial
infarction" should see it via get_entity()/resolve_ambiguity(), not
re-extract it blind). A bare dict's check-then-set in register_entity()
is not atomic under real concurrent access, so every public method here
takes self._lock — the one piece of this package that touches
threading.Lock directly, so nothing else has to.
"""

import threading
from dataclasses import dataclass, field
from typing import Optional

from .enums import ClinicalEntityType
from .models import ClinicalEntity, ClinicalRelation
from .normalizers import AMBIGUOUS_ABBREVIATIONS


def _key(value: str, entity_type: ClinicalEntityType) -> str:
    return f"{entity_type.value}:{value.strip().lower()}"


@dataclass
class EntityRegistry:
    """See module docstring. One instance per pipeline run — never
    shared across documents (entities from one document must never leak
    into another's result)."""

    entities: dict[str, ClinicalEntity] = field(default_factory=dict)
    relations: list[ClinicalRelation] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def get_entity(self, value: str, entity_type: ClinicalEntityType) -> Optional[ClinicalEntity]:
        with self._lock:
            return self.entities.get(_key(value, entity_type))

    def all_entities(self) -> list[ClinicalEntity]:
        """A stable snapshot list of every registered entity — see
        entities_by_type()'s own docstring for why this takes the lock
        rather than callers reading `.entities.values()` directly."""
        with self._lock:
            return list(self.entities.values())

    def register_entity(self, entity: ClinicalEntity) -> ClinicalEntity:
        """Registers `entity`, or returns the already-registered entity
        for the same (value, entity_type) if one exists — first-seen
        wins (see deduplicators.py for confidence-based merging across
        near-duplicate raw text, a different concern from this exact-key
        dedup)."""
        key = _key(entity.value, entity.entity_type)
        with self._lock:
            existing = self.entities.get(key)
            if existing is not None:
                return existing
            self.entities[key] = entity
            return entity

    def register_relation(self, relation: ClinicalRelation) -> None:
        with self._lock:
            self.relations.append(relation)

    def resolve_ambiguity(self, value: str) -> list[ClinicalEntity]:
        """Every already-registered entity matching one of `value`'s
        known possible meanings — empty if `value` isn't a known-
        ambiguous term, or if none of its possible meanings have been
        seen yet elsewhere in this document."""
        candidates = AMBIGUOUS_ABBREVIATIONS.get(value.strip().lower(), ())
        if not candidates:
            return []
        with self._lock:
            return [entity for entity in self.entities.values() if entity.value.lower() in candidates]

    def entities_by_type(self, entity_type: ClinicalEntityType) -> list[ClinicalEntity]:
        """A stable snapshot list of every registered entity of
        `entity_type` — the safe way for a downstream extractor (e.g.
        interventions.py, wanting every already-registered DRUG/
        PROCEDURE entity clinical_entities.py found) to iterate this
        registry's contents. Iterating `.entities.values()` directly
        from a caller would race against another thread's
        register_entity() call under real parallel execution (see
        module docstring) — this takes the lock once and returns a
        plain list, safe to iterate afterward with no lock held."""
        with self._lock:
            return [entity for entity in self.entities.values() if entity.entity_type == entity_type]
