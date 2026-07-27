"""Evidence and reasoning builders — the one place a winning label (from
confidence.resolve()) gets turned into a full ClassificationDecision,
shared by all four detectors so none of them repeats this glue.

evidence is built from the *per-source* SignalMatch dicts a detector
already has on hand (one dict per signal source — keywords, venue,
structural features, ...), not from
backend.classification.pass1.rules.combine_signals()'s own flat,
all-labels reasoning list — that list interleaves every candidate
label's reasoning, not just the winner's, so picking the winning label's
own SignalMatch.reasoning out of each source dict directly is simpler
and exact rather than string-matching the combined list back apart.

Note evidence is necessarily always empty when `label` is the
unknown/fallback member: nothing in any keyword/venue/structural map is
ever keyed by UNKNOWN, so no source dict ever contains it. _summarize()
below handles that case from confidence.resolve()'s preserved
sub-threshold confidence instead of from evidence, so a "close but not
quite" decision still gets a useful reasoning string rather than always
falling back to None (see confidence.resolve()'s own docstring on why
that real sub-threshold number is kept rather than zeroed).
"""

from typing import Optional, TypeVar

from backend.classification.pass1.rules import SignalMatch

from .models import ClassificationDecision

_Label = TypeVar("_Label")


def build_decision(
    label: _Label,
    confidence: float,
    signal_sources: list[dict[_Label, SignalMatch]],
    unknown_label: _Label,
) -> ClassificationDecision:
    """Builds label's ClassificationDecision from whichever of
    `signal_sources` actually matched it — sources that didn't match
    `label` at all (including every source, when `label` is the
    unknown/fallback member) simply contribute no evidence."""
    evidence = [source[label].reasoning for source in signal_sources if label in source]
    return ClassificationDecision(
        label=label,
        confidence=confidence,
        evidence=evidence,
        reasoning=_summarize(label, confidence, evidence, unknown_label),
    )


def _summarize(label: _Label, confidence: float, evidence: list[str], unknown_label: _Label) -> Optional[str]:
    if label == unknown_label:
        if confidence <= 0.0:
            return None  # nothing matched anything at all — no summary needed
        return f"No label cleared the confidence threshold (best candidate confidence {confidence:.2f})."
    if not evidence:
        return None
    label_text = getattr(label, "value", label)
    return f"Classified as {label_text!r} with confidence {confidence:.2f} based on {len(evidence)} matched signal(s)."
