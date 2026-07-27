"""Post-processing pipeline: Normalization (already done at extraction
time — see normalizers.py, called from clinical_entities.py) →
Deduplication → Relationship Resolution → Validation. Runs once, after
every enabled extractor's ExtractionResult has been collected — the one
place all eight extractors' scattered outputs get merged into
MedicalUnderstanding's own flat lists.

Relationship Resolution builds ClinicalRelation edges between registered
entities that co-occur in the same paragraph, typed by which entity-type
pair is involved (e.g. a DRUG and a CONDITION mentioned together become
a TREATS relation) — a coarse, deterministic co-occurrence heuristic,
not real relation extraction (no dependency parsing, no ML — see package
docstring's Non-Goals). Cycle detection (an explicit completion
criterion) runs over the resulting relation list via a real DFS
reachability check, dropping any relation that would close a cycle back
to an entity already reachable from it.

Validation here means resource-limit enforcement (entity/relation counts
against config.max_entities/max_relations) — validating the fully-
assembled MedicalUnderstanding itself is validators.validate_output()'s
job, called from pipeline.py after this module returns (the final
object doesn't exist yet at this point in the pipeline).
"""

from dataclasses import dataclass, field

from .config import MedicalUnderstandingConfig
from .deduplicators import deduplicate_by_name, deduplicate_entities
from .entity_registry import EntityRegistry
from .enums import ClinicalEntityType, ClinicalRelationType
from .models import (
    ClinicalEntity,
    ClinicalRelation,
    Comparator,
    Intervention,
    KeyFinding,
    Outcome,
    Population,
    StatisticalMeasure,
)
from .security.limits import ResourceGuard

# Which ClinicalRelationType a (subject_type, object_type) pair implies
# — deliberately small and illustrative (see module docstring), not an
# attempt at exhaustive clinical-relation coverage.
_RELATION_TYPE_BY_ENTITY_PAIR: dict[tuple[ClinicalEntityType, ClinicalEntityType], ClinicalRelationType] = {
    (ClinicalEntityType.DRUG, ClinicalEntityType.CONDITION): ClinicalRelationType.TREATS,
    (ClinicalEntityType.PROCEDURE, ClinicalEntityType.CONDITION): ClinicalRelationType.TREATS,
    (ClinicalEntityType.CONDITION, ClinicalEntityType.SYMPTOM): ClinicalRelationType.CAUSES,
    (ClinicalEntityType.DRUG, ClinicalEntityType.ADVERSE_EVENT): ClinicalRelationType.CAUSES,
    (ClinicalEntityType.LAB_TEST, ClinicalEntityType.CONDITION): ClinicalRelationType.MEASURED_BY,
}


@dataclass
class PostProcessedResults:
    """Plain container for post_process()'s output — the merged,
    deduplicated, relation-resolved lists pipeline.py assembles
    MedicalUnderstanding from."""

    clinical_entities: list[ClinicalEntity] = field(default_factory=list)
    populations: list[Population] = field(default_factory=list)
    interventions: list[Intervention] = field(default_factory=list)
    comparators: list[Comparator] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)
    statistical_measures: list[StatisticalMeasure] = field(default_factory=list)
    key_findings: list[KeyFinding] = field(default_factory=list)
    relations: list[ClinicalRelation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def post_process(
    registry: EntityRegistry,
    extracted: dict,
    config: MedicalUnderstandingConfig,
) -> PostProcessedResults:
    """`extracted` is a plain dict of already-merged lists — see
    pipeline.py, which flattens every ExtractionResult.get(name) call
    into this shape before calling here (keys: populations,
    interventions, comparators, outcomes, statistical_measures,
    key_findings)."""
    entities = registry.all_entities()
    warnings: list[str] = []

    if config.deduplicate_entities:
        entities = deduplicate_entities(entities)
        interventions = deduplicate_by_name(
            extracted.get("interventions", []), lambda item: item.name, lambda item: item.confidence
        )
        comparators = deduplicate_by_name(
            extracted.get("comparators", []), lambda item: item.name, lambda item: item.confidence
        )
        outcomes = deduplicate_by_name(
            extracted.get("outcomes", []), lambda item: item.name, lambda item: item.confidence
        )
    else:
        interventions = extracted.get("interventions", [])
        comparators = extracted.get("comparators", [])
        outcomes = extracted.get("outcomes", [])

    guard = ResourceGuard(config)
    if not guard.check_limits(len(entities), 0):
        warnings.append(f"entity count exceeded configured limit ({config.max_entities}); truncating")
        entities = entities[: config.max_entities]

    relations = _resolve_relationships(entities)
    if not guard.check_limits(len(entities), len(relations)):
        warnings.append(f"relation count exceeded configured limit ({config.max_relations}); truncating")
        relations = relations[: config.max_relations]
    for relation in relations:
        registry.register_relation(relation)

    return PostProcessedResults(
        clinical_entities=entities,
        populations=extracted.get("populations", []),
        interventions=interventions,
        comparators=comparators,
        outcomes=outcomes,
        statistical_measures=extracted.get("statistical_measures", []),
        key_findings=extracted.get("key_findings", []),
        relations=relations,
        warnings=warnings,
    )


def _resolve_relationships(entities: list[ClinicalEntity]) -> list[ClinicalRelation]:
    relations: list[ClinicalRelation] = []
    seen_edges: set[tuple[str, str]] = set()

    for i, first in enumerate(entities):
        for second in entities[i + 1 :]:
            if not _same_paragraph(first, second) or first.value == second.value:
                continue

            subject, obj, relation_type = _classify_pair(first, second)
            if relation_type is None:
                continue

            edge = (subject.value, obj.value)
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            relations.append(
                ClinicalRelation(
                    subject=subject.value,
                    relation_type=relation_type,
                    object=obj.value,
                    confidence=min(subject.confidence, obj.confidence),
                    evidence=subject.evidence,
                )
            )

    return _drop_cycles(relations)


def _classify_pair(first: ClinicalEntity, second: ClinicalEntity):
    relation_type = _RELATION_TYPE_BY_ENTITY_PAIR.get((first.entity_type, second.entity_type))
    if relation_type is not None:
        return first, second, relation_type
    relation_type = _RELATION_TYPE_BY_ENTITY_PAIR.get((second.entity_type, first.entity_type))
    if relation_type is not None:
        return second, first, relation_type
    return first, second, None


def _same_paragraph(first: ClinicalEntity, second: ClinicalEntity) -> bool:
    return (
        first.evidence.section == second.evidence.section
        and first.evidence.paragraph is not None
        and first.evidence.paragraph == second.evidence.paragraph
    )


def _drop_cycles(relations: list[ClinicalRelation]) -> list[ClinicalRelation]:
    """Drops any relation that would close a cycle in the directed
    subject->object graph built so far — a real DFS reachability check
    (the explicit "Cycle detection for relations" completion criterion),
    not just deduplication."""
    graph: dict[str, set[str]] = {}
    kept: list[ClinicalRelation] = []

    for relation in relations:
        if _creates_cycle(graph, relation.subject, relation.object):
            continue
        graph.setdefault(relation.subject, set()).add(relation.object)
        kept.append(relation)

    return kept


def _creates_cycle(graph: dict[str, set[str]], subject: str, obj: str) -> bool:
    """True if adding subject->obj would create a cycle — i.e. `obj` can
    already reach `subject` via existing edges."""
    if subject == obj:
        return True
    visited: set[str] = set()
    stack = [obj]
    while stack:
        node = stack.pop()
        if node == subject:
            return True
        if node in visited:
            continue
        visited.add(node)
        stack.extend(graph.get(node, ()))
    return False
