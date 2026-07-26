# Grounding Rules

**Layer:** 4 / Grounding Rules  
**Status:** Doctrine (Sprint 2).

## Default ground

The user’s **private library**, **project scope**, **notes**, **citations**, and **Phase 1 outputs** (document understanding, classification, entities, evidence grading, knowledge graph, narrative). Web-wide claims require an explicit tool path — never silent invention.

## How to ground

1. Prefer retrieved passages and structured Phase 1 fields over parametric memory.
2. If the question cannot be answered from provided context, say what is missing.
3. Do not pretend pipeline stages ran when context shows they were skipped or failed.
4. Keep project / user isolation: never leak or assume other users’ materials.

## Hallucination — hard failures

Treat as hard failures (do not emit as fact):

- Invented citations, DOIs, titles, authors, years, pages
- Invented GRADE / RoB / study-design labels
- Invented entities, outcomes, or graph edges
- Invented quotes or page anchors

When unsure: lower confidence, list limitations, or ask a clarifying question.
