"""Legacy Paper Chat system prompt (Stage 1 — behaviour-identical).

Canonical text for ``LEGACY_PAPER_CHAT_PROMPT_VERSION``.
Do not prepend IdentityPack here — that is Stage 2+.
"""

from __future__ import annotations

from datetime import datetime


def render_legacy_paper_chat_prompt(
    *,
    user_name: str,
    paper_title: str,
    authors: str | None = None,
    year: int | str | None = None,
    venue: str | None = None,
    now: datetime | None = None,
) -> str:
    """Exact Paper Chat system instructions (M7 parity).

    Matches historical ``server.build_paper_chat_prompt`` output for the same
    inputs. ``now`` is injectable for golden tests.
    """
    when = now or datetime.now()
    header = (
        "You are an expert research assistant helping a researcher understand "
        "the paper titled: " + repr(paper_title) + "."
    )
    body = (
        "Answer questions, explain concepts, and clarify content from THIS PAPER ONLY.\n\n"
        "Rules:\n"
        "1. Answer ONLY using content from the retrieved excerpts of this paper.\n"
        "2. Never fabricate data, citations, numbers, or conclusions.\n"
        "3. When citing, specify page and section where available: "
        "e.g. 'According to p. 4, Section: Methodology...'.\n"
        "4. If the answer is not in the excerpts, say: "
        "'I cannot find that in this paper. Try rephrasing your question or "
        "specifying a section.'\n"
        "5. Do not use web search or external knowledge.\n"
        "6. Use markdown for clarity."
    )
    meta = [
        f"User: {user_name}",
        f"Date: {when.strftime('%Y-%m-%d %H:%M')}",
    ]
    if authors:
        meta.append(f"Authors: {authors}")
    if year:
        meta.append(f"Year: {year}")
    if venue:
        meta.append(f"Venue: {venue}")
    return header + "\n\n" + body + "\n\n" + "\n".join(meta)
