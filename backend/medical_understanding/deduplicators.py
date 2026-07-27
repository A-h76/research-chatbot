"""Entity deduplication — a post-processing pass, complementary to (not
a replacement for) entity_registry.py's own exact-key dedup at
registration time. entity_registry.py catches two extractors registering
the identical (value, entity_type) pair; deduplicate_entities() catches
near-duplicates that slipped through because their `value` strings
differ (e.g. "diabetes" vs "diabetes mellitus") by merging them through
normalizers.py's own deterministic fuzzy-match logic.

deduplicate_by_name() is the same idea, generalized for post_processor.py's
other domain lists (Population/Intervention/Comparator/Outcome), which
don't need normalizers.py's clinical-vocabulary matching — just literal
near-identical-name collapsing, keeping the highest-confidence entry.
"""

from typing import Callable, TypeVar

from .models import ClinicalEntity
from .normalizers import normalize

_Item = TypeVar("_Item")


def deduplicate_entities(entities: list[ClinicalEntity]) -> list[ClinicalEntity]:
    """Merges near-duplicate entities (same entity_type, normalizing to
    the same canonical value) into the single highest-confidence one,
    combining their synonyms — never drops evidence, only keeps the
    entity whose own evidence/confidence is judged best."""
    best_by_key: dict[tuple[str, str], ClinicalEntity] = {}
    for entity in entities:
        canonical, _, _ = normalize(entity.value)
        key = (entity.entity_type.value, canonical)
        existing = best_by_key.get(key)
        if existing is None:
            best_by_key[key] = entity
        elif entity.confidence > existing.confidence:
            entity.synonyms = sorted(set(entity.synonyms) | set(existing.synonyms))
            best_by_key[key] = entity
        else:
            existing.synonyms = sorted(set(existing.synonyms) | set(entity.synonyms))
    return list(best_by_key.values())


def deduplicate_by_name(
    items: list[_Item],
    name_getter: Callable[[_Item], str],
    confidence_getter: Callable[[_Item], float],
) -> list[_Item]:
    """Keeps the highest-confidence item per distinct (stripped,
    lowercased) name — see module docstring."""
    best_by_name: dict[str, _Item] = {}
    for item in items:
        key = name_getter(item).strip().lower()
        if not key:
            continue
        existing = best_by_name.get(key)
        if existing is None or confidence_getter(item) > confidence_getter(existing):
            best_by_name[key] = item
    return list(best_by_name.values())
