"""Confidence resolution — turns a detector's ranked (label, score) list
into a final decision, applying the "never guess when uncertain" rule.

The actual scoring/aggregation (weighted keyword/venue/structural-feature
matching) is NOT reimplemented here — every detector in this package
calls backend.classification.pass1.rules' match_keywords()/match_venue()/
match_structural_features()/combine_signals() directly, the same pure,
generic engine pass1's own domain.py/type.py/publication.py are built on
(see package docstring: pass1 is a stable, unmodified dependency). This
module only owns the one piece of logic that's genuinely new to Pass 2:
deciding whether the winning label clears the confidence bar at all.
"""

from typing import TypeVar

_Label = TypeVar("_Label")
_Signals = dict[_Label, object]

# Below this, a label's evidence is too weak to report with confidence —
# the detector falls back to that family's own UNKNOWN (or, for
# ReportingGuideline, NONE/UNKNOWN) member instead of guessing.
CONFIDENCE_THRESHOLD = 0.3


def active_sources(*sources: tuple[_Signals, float]) -> list[tuple[_Signals, float]]:
    """Drops any (signals, weight) pair whose `signals` dict is empty
    before it reaches pass1.rules.combine_signals().

    combine_signals() divides by the *full* weight of every source
    passed to it, including one that matched nothing for any label (see
    its own docstring: "sum(source_weight for every source passed in)").
    A detector calling it with, say, (venue_signals, 2.0) alongside
    (keyword_signals, 1.0) means a document with no recognized venue —
    common; Phase 1.1's venue extraction is a best-effort heuristic, not
    guaranteed — has its keyword-only score cut to keyword_weight /
    (venue_weight + keyword_weight) even though venue contributed
    nothing, capping it below CONFIDENCE_THRESHOLD regardless of how
    strong the keyword match actually is. Every detector in this package
    calls combine_signals() through this filter, not directly, so an
    empty source's weight is simply absent from the denominator instead
    of silently diluting every candidate's score."""
    return [(signals, weight) for signals, weight in sources if signals]


def resolve(ranked: list[tuple[_Label, float]], unknown_label: _Label) -> tuple[_Label, float]:
    """Returns (label, confidence) — the top-ranked entry in `ranked` if
    it clears CONFIDENCE_THRESHOLD, otherwise `unknown_label` paired with
    whatever confidence was actually computed (0.0 if `ranked` is empty,
    i.e. no signal matched anything at all; the real sub-threshold score
    otherwise, so callers can see *how close* it came rather than just a
    flat 0.0)."""
    if not ranked:
        return unknown_label, 0.0

    label, confidence = ranked[0]
    if confidence < CONFIDENCE_THRESHOLD:
        return unknown_label, confidence
    return label, confidence
