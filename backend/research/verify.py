"""Lightweight chat answer grounding check (W4).

Deterministic overlap against retrieved passages — no extra LLM call.
Reports confidence + researcher-facing warnings for the Trust Chat surface.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Optional

from .retrieve import PassageHit

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[a-z0-9][a-z0-9\-]{2,}", re.I)

# Ultra-common tokens that don't prove grounding.
_STOP = frozenset(
    """
    the and for that this with from are was were been being have has had
    not but you your our their they them its it's into than then also
    can may might should would could will about over under such into onto
    using based between among within without through during before after
    """.split()
)


@dataclass(frozen=True)
class GroundingReport:
    confidence: float
    supported_ratio: float
    substantive_sentences: int
    supported_sentences: int
    warnings: tuple[str, ...]
    skill: str = "ask"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_chat_grounding(
    answer: str,
    passages: list[PassageHit],
    *,
    skill: str = "ask",
    min_overlap: float = 0.28,
) -> GroundingReport:
    """Score how well ``answer`` is lexically supported by ``passages``."""
    corpus = "\n".join((p.content or "") for p in passages).lower()
    corpus_tokens = _content_tokens(corpus)

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(answer or "") if s.strip()]
    substantive = [s for s in sentences if len(_content_tokens(s)) >= 4]

    if not substantive:
        return GroundingReport(
            confidence=0.0 if passages else 0.0,
            supported_ratio=0.0,
            substantive_sentences=0,
            supported_sentences=0,
            warnings=(
                ("No retrieved passages — answer may be ungrounded.",)
                if not passages
                else ("Answer was too short to verify grounding.",)
            ),
            skill=skill,
        )

    if not passages or not corpus_tokens:
        return GroundingReport(
            confidence=0.15,
            supported_ratio=0.0,
            substantive_sentences=len(substantive),
            supported_sentences=0,
            warnings=("No document passages were retrieved for this turn.",),
            skill=skill,
        )

    supported = 0
    for s in substantive:
        tokens = _content_tokens(s)
        if not tokens:
            continue
        hits = sum(1 for t in tokens if t in corpus_tokens)
        if hits / len(tokens) >= min_overlap:
            supported += 1

    ratio = supported / len(substantive)
    # Soften slightly when few passages
    conf = round(min(1.0, ratio * (0.85 + 0.15 * min(1.0, len(passages) / 4))), 3)

    warnings: list[str] = []
    if ratio < 0.45:
        warnings.append(
            "Low grounding — several statements may not be supported by the retrieved passages."
        )
    elif ratio < 0.7:
        warnings.append(
            "Partial grounding — verify claims against the Passages chips before citing."
        )
    if len(passages) < 2 and skill in ("synthesize", "compare"):
        warnings.append(
            "Few passages retrieved for a multi-source skill — broaden scope or rephrase the question."
        )

    return GroundingReport(
        confidence=conf,
        supported_ratio=round(ratio, 3),
        substantive_sentences=len(substantive),
        supported_sentences=supported,
        warnings=tuple(warnings),
        skill=skill,
    )


def _content_tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "") if w.lower() not in _STOP}
