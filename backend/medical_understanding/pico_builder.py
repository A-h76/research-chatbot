"""PICOBuilder — assembles PICOElements from already-extracted
Population/Intervention/Comparator/Outcome lists. Not a new extraction
pass: population is simply the first (or only) entry in the already-
extracted list (populations.py only ever produces one Population per
document); interventions/comparators/outcomes are passed through as-is.

This module isn't in the originating task's own directory tree — only
in its dependency graph ("PICOBuilder └── Assembles PICO from extracted
components") and its Implementation Order ("21. pico_builder.py") — see
models.py's PICOElements docstring for the same gap.
"""

from typing import Optional

from .models import Comparator, Intervention, Outcome, PICOElements, Population


def build_pico(
    populations: list[Population],
    interventions: list[Intervention],
    comparators: list[Comparator],
    outcomes: list[Outcome],
) -> PICOElements:
    population = populations[0] if populations else None
    return PICOElements(
        population=population,
        interventions=interventions,
        comparators=comparators,
        outcomes=outcomes,
        confidence=_confidence(population, interventions, comparators, outcomes),
    )


def _confidence(
    population: Optional[Population],
    interventions: list[Intervention],
    comparators: list[Comparator],
    outcomes: list[Outcome],
) -> float:
    scores: list[float] = []
    if population is not None:
        scores.append(population.confidence)
    scores.extend(intervention.confidence for intervention in interventions)
    scores.extend(comparator.confidence for comparator in comparators)
    scores.extend(outcome.confidence for outcome in outcomes)
    return sum(scores) / len(scores) if scores else 0.0
