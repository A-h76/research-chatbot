"""Confidence aggregation — combines this package's five profiles into
one ConfidenceScore. Plain mean across the five breakdown fields, not a
re-weighted hidden recombination (see models.py's ConfidenceScore
docstring for why — same transparency choice backend.classification.
pass1's classify_document() and backend.document_understanding's
DocumentQuality both already make).

SectionProfile has no single confidence field of its own (only a per-
SectionType section_confidence dict — see models.py) — its contribution
here is the mean of that dict's values, 0.0 if no section was detected
at all.
"""

from .models import AnalysisProfile, ConfidenceScore, DocumentProfile, PromptProfile, RoutingProfile, SectionProfile


def compute_confidence(
    document_profile: DocumentProfile,
    section_profile: SectionProfile,
    analysis_profile: AnalysisProfile,
    routing_profile: RoutingProfile,
    prompt_profile: PromptProfile,
) -> ConfidenceScore:
    section_confidence = _section_confidence(section_profile)
    breakdown = (
        document_profile.confidence,
        section_confidence,
        analysis_profile.confidence,
        routing_profile.confidence,
        prompt_profile.confidence,
    )
    return ConfidenceScore(
        overall=sum(breakdown) / len(breakdown),
        document_profile=document_profile.confidence,
        section_profile=section_confidence,
        analysis_profile=analysis_profile.confidence,
        routing_profile=routing_profile.confidence,
        prompt_profile=prompt_profile.confidence,
    )


def _section_confidence(section_profile: SectionProfile) -> float:
    if not section_profile.section_confidence:
        return 0.0
    return sum(section_profile.section_confidence.values()) / len(section_profile.section_confidence)
