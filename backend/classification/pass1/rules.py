"""Rule engine — the shared weighted keyword/venue/structural matching
and score-combination logic every Pass 1 classifier (domain.py, type.py,
publication.py) is built on. Deterministic only (rule: "prefer
deterministic rule-based classification first... do not implement
ML/LLM classifiers now") — every function here is plain substring
matching and arithmetic, no model call. A future ML/LLM classifier is a
new module implementing the same *classifier* interface (e.g. a second
DomainClassifier-shaped class), not a change here.

Centralizing this scoring mechanism (rather than each classifier
re-implementing its own matching/weighting) is what keeps
domain.py/type.py/publication.py "highly cohesive" (rule #7) — each is
just its own keyword/venue/feature data plus which signals to combine at
what weight; none of them re-derives how a single signal turns into a
confidence number.
"""

from dataclasses import dataclass


@dataclass
class SignalMatch:
    """One scoring signal's evidence for one candidate label.

    Attributes:
        label: The candidate this evidence supports (e.g. "medical").
        weight: This signal's own confidence for the label, 0.0-1.0 —
            not yet combined with other signals' weights.
        matched_terms: The literal keywords/phrases/venue substrings that
            matched, for matched_features.
        reasoning: One human-readable sentence explaining this match.
    """

    label: str
    weight: float
    matched_terms: list[str]
    reasoning: str


def match_keywords(text: str, keyword_map: dict[str, list[str]]) -> dict[str, SignalMatch]:
    """Scores every label in `keyword_map` by the fraction of its own
    keyword list found in `text` (case-insensitive substring match).
    Labels with zero matches are omitted entirely — a 0.0 score with no
    evidence isn't useful to callers, and combine_signals() below treats
    "no entry for this label from this source" the same as "found
    nothing" anyway.
    """
    lowered = (text or "").lower()
    results: dict[str, SignalMatch] = {}
    if not lowered:
        return results

    for label, keywords in keyword_map.items():
        matched = [kw for kw in keywords if kw.lower() in lowered]
        if matched:
            weight = len(matched) / len(keywords)
            results[label] = SignalMatch(
                label=label,
                weight=weight,
                matched_terms=matched,
                reasoning=f"{len(matched)}/{len(keywords)} {label} keyword(s) matched: {', '.join(matched)}",
            )
    return results


def match_venue(venue: str, venue_map: dict[str, list[str]]) -> dict[str, SignalMatch]:
    """Same idea as match_keywords(), scoped to a single venue string.
    A venue matching even one known substring is treated as full
    confidence (1.0) for that label — a venue name is a much stronger,
    less ambiguous signal than a body-text keyword (e.g. a venue
    literally named "NeurIPS" is unambiguous; the word "algorithm"
    appearing in text is weaker evidence on its own)."""
    lowered = (venue or "").lower()
    results: dict[str, SignalMatch] = {}
    if not lowered:
        return results

    for label, venues in venue_map.items():
        matched = [v for v in venues if v.lower() in lowered]
        if matched:
            results[label] = SignalMatch(
                label=label,
                weight=1.0,
                matched_terms=matched,
                reasoning=f"venue matches known {label} venue {matched[0]!r}",
            )
    return results


def match_structural_features(
    present_features: set[str], feature_map: dict[str, tuple[str, ...]]
) -> dict[str, SignalMatch]:
    """Scores every label in `feature_map` by the fraction of its
    expected structural features (e.g. "has_methods") that are present
    on the document (backend.processing.models.DocumentQuality's own
    has_* flags, passed in as a set of the flag names that are True)."""
    results: dict[str, SignalMatch] = {}
    for label, expected_features in feature_map.items():
        matched = [f for f in expected_features if f in present_features]
        if matched:
            weight = len(matched) / len(expected_features)
            results[label] = SignalMatch(
                label=label,
                weight=weight,
                matched_terms=matched,
                reasoning=f"{len(matched)}/{len(expected_features)} structural feature(s) present: {', '.join(matched)}",
            )
    return results


def combine_signals(
    *weighted_sources: tuple[dict[str, SignalMatch], float],
) -> tuple[list[tuple[str, float]], list[str], dict[str, list[str]]]:
    """Combines multiple (signals, source_weight) pairs into one ranked
    label list plus aggregated reasoning/matched_features.

    confidence(label) = sum(signal.weight * source_weight for every
    source that found this label) / sum(source_weight for every source
    passed in) — a weighted average across sources. A label only one of
    three sources found still scores lower than one two sources agree
    on, proportional to how much weight that one source carries; a label
    no source found at all never appears in the output list.

    Returns (ranked_labels, reasoning, matched_features):
      ranked_labels: [(label, confidence), ...] descending by confidence.
      reasoning: every contributing SignalMatch's reasoning string, in
        the order sources were passed in.
      matched_features: label -> every matched term from every source
        that found it (deduplicated, insertion order preserved).
    """
    total_weight = sum(source_weight for _, source_weight in weighted_sources)
    if total_weight <= 0:
        return [], [], {}

    scores: dict[str, float] = {}
    reasoning: list[str] = []
    matched_features: dict[str, list[str]] = {}

    all_labels: list[str] = []
    seen_labels: set[str] = set()
    for signals, _ in weighted_sources:
        for label in signals:
            if label not in seen_labels:
                seen_labels.add(label)
                all_labels.append(label)

    for label in all_labels:
        score = 0.0
        for signals, source_weight in weighted_sources:
            hit = signals.get(label)
            if hit is None:
                continue
            score += hit.weight * source_weight
            reasoning.append(hit.reasoning)
            bucket = matched_features.setdefault(label, [])
            for term in hit.matched_terms:
                if term not in bucket:
                    bucket.append(term)
        scores[label] = score / total_weight

    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return ranked, reasoning, matched_features
