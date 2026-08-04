"""UFTR orchestrator — resolve candidates, validate, optionally attach."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

from backend.scholarly.uftr.cache import get_cached_resolution, store_resolution
from backend.scholarly.uftr.outcomes import (
    FullTextOutcome,
    ResolutionAttempt,
    ResolutionResult,
    content_kind_for_bytes,
)
from backend.scholarly.uftr.resolvers import collect_candidates, hints_from_user_file
from backend.scholarly.uftr.validator import download_candidate, filename_from_url

logger = logging.getLogger(__name__)

_MAX_CANDIDATES = int(os.environ.get("UFTR_MAX_CANDIDATES", "6"))


def _rank_failure(outcomes: list[FullTextOutcome]) -> FullTextOutcome:
    """Prefer the most informative terminal failure for analytics/UI."""
    if not outcomes:
        return FullTextOutcome.NO_OPEN_ACCESS
    priority = [
        FullTextOutcome.BOT_PROTECTION,
        FullTextOutcome.PUBLISHER_PAYWALL,
        FullTextOutcome.INVALID_RESPONSE,
        FullTextOutcome.TIMEOUT,
        FullTextOutcome.NETWORK_ERROR,
        FullTextOutcome.NO_OPEN_ACCESS,
    ]
    for p in priority:
        if p in outcomes:
            return p
    return outcomes[-1]


def resolve_full_text(
    *,
    doi: str = "",
    open_access_url: str = "",
    source_url: str = "",
    pmcid: str = "",
    arxiv_id: str = "",
    provider: str = "",
    db: Any = None,
    max_bytes: int = 50 * 1024 * 1024,
    use_cache: bool = True,
    force: bool = False,
) -> ResolutionResult:
    """Run Resolver Chain → Validator. Does not attach bytes to storage.

    When ``use_cache`` and a fresh negative cache hit exists (no FOUND URL),
    skip re-hammering resolvers unless ``force``. FOUND cache still re-validates
    the URL (OA links rot).
    """
    from backend.scholarly import provider_enabled

    if not provider_enabled("uftr"):
        return ResolutionResult(
            outcome=FullTextOutcome.NO_OPEN_ACCESS,
            attempts=[
                ResolutionAttempt(
                    resolver="uftr",
                    outcome=FullTextOutcome.NO_OPEN_ACCESS,
                    reason="uftr_disabled",
                )
            ],
        )

    doi = (doi or "").strip()
    provider_id = ""
    if provider and (pmcid or arxiv_id):
        provider_id = f"{provider}:{pmcid or arxiv_id}"

    if use_cache and not force and db is not None:
        cached = get_cached_resolution(db, doi=doi, provider_id=provider_id)
        if isinstance(cached, dict):
            outcome_s = (cached.get("outcome") or "").strip()
            # Skip discovery only for stable negatives — not FOUND (re-validate URL)
            if outcome_s in {
                FullTextOutcome.NO_OPEN_ACCESS.value,
                FullTextOutcome.PUBLISHER_PAYWALL.value,
                FullTextOutcome.BOT_PROTECTION.value,
            }:
                try:
                    outcome = FullTextOutcome(outcome_s)
                except ValueError:
                    outcome = FullTextOutcome.NO_OPEN_ACCESS
                return ResolutionResult(
                    outcome=outcome,
                    attempts=[
                        ResolutionAttempt(
                            resolver="cache",
                            outcome=outcome,
                            reason="cached_negative",
                            url=(cached.get("url") or "")[:500],
                        )
                    ],
                    full_text_source=cached.get("full_text_source") or "",
                    url=(cached.get("url") or "")[:500],
                )

    candidates = collect_candidates(
        doi=doi,
        open_access_url=open_access_url,
        source_url=source_url,
        pmcid=pmcid,
        arxiv_id=arxiv_id,
        provider=provider,
        db=db,
    )

    attempts: list[ResolutionAttempt] = []
    fail_outcomes: list[FullTextOutcome] = []

    if not candidates:
        result = ResolutionResult(
            outcome=FullTextOutcome.NO_OPEN_ACCESS,
            attempts=[
                ResolutionAttempt(
                    resolver="chain",
                    outcome=FullTextOutcome.NO_OPEN_ACCESS,
                    reason="no_candidates",
                )
            ],
        )
        if db is not None:
            store_resolution(
                db,
                doi=doi,
                provider_id=provider_id,
                payload=result.to_public_dict(),
                outcome=result.outcome,
            )
        return result

    for cand in candidates[: max(1, _MAX_CANDIDATES)]:
        outcome, data, _ctype, final_url = download_candidate(
            cand.url,
            max_bytes=max_bytes,
        )
        attempts.append(
            ResolutionAttempt(
                resolver=cand.resolver,
                outcome=outcome,
                reason=cand.hint or outcome.value.lower(),
                url=final_url or cand.url,
            )
        )
        if outcome == FullTextOutcome.FOUND and data:
            result = ResolutionResult(
                outcome=FullTextOutcome.FOUND,
                attempts=attempts,
                data=data,
                filename=filename_from_url(
                    final_url or cand.url,
                    fallback=f"{(doi or pmcid or arxiv_id or 'fulltext').replace('/', '_')}.pdf",
                ),
                content_kind=content_kind_for_bytes(data),
                full_text_source=cand.resolver,
                url=final_url or cand.url,
            )
            if db is not None:
                store_resolution(
                    db,
                    doi=doi,
                    provider_id=provider_id,
                    payload=result.to_public_dict(),
                    outcome=result.outcome,
                )
            return result
        fail_outcomes.append(outcome)

    final = _rank_failure(fail_outcomes)
    result = ResolutionResult(
        outcome=final,
        attempts=attempts,
        url=(attempts[-1].url if attempts else ""),
    )
    if db is not None:
        store_resolution(
            db,
            doi=doi,
            provider_id=provider_id,
            payload=result.to_public_dict(),
            outcome=result.outcome,
        )
    return result


def resolve_from_user_file(
    uf: Any,
    *,
    db: Any = None,
    max_bytes: int = 50 * 1024 * 1024,
    force: bool = False,
) -> ResolutionResult:
    hints = hints_from_user_file(uf)
    return resolve_full_text(
        doi=hints["doi"],
        open_access_url=hints["open_access_url"],
        source_url=hints["source_url"],
        pmcid=hints["pmcid"],
        arxiv_id=hints["arxiv_id"],
        provider=hints["provider"],
        db=db,
        max_bytes=max_bytes,
        force=force,
    )


def resolve_and_attach(
    db: Any,
    uf: Any,
    *,
    storage,
    upload_dir: str,
    enqueue_import: Callable | None,
    user_id: int,
    max_file_mb: int = 50,
    force: bool = False,
    work: Any = None,
) -> dict[str, Any]:
    """UFTR → apply_pdf_bytes_to_stub on FOUND. Persists fulltext_json either way.

    Returns attach_meta compatible with Discover import response:
      pdf_attached, analysis_queued, pdf_error, fulltext (public dict)
    """
    from backend.library.file_pull import apply_pdf_bytes_to_stub
    from backend.library.sync import has_research_asset
    from backend.scholarly.uftr.state import apply_resolution_to_file, mark_resolving

    out: dict[str, Any] = {
        "pdf_attached": False,
        "analysis_queued": False,
        "pdf_error": None,
        "fulltext": None,
    }

    if storage is None or not upload_dir:
        out["pdf_error"] = "pipeline_not_wired"
        return out

    if has_research_asset(uf):
        out["pdf_error"] = "already_has_pdf"
        return out

    mark_resolving(uf, on=True)
    try:
        db.flush()
    except Exception:
        pass

    hints = hints_from_user_file(uf)
    # Prefer live work object fields when Discover passes them
    if work is not None:
        hints["doi"] = (getattr(work, "doi", None) or hints["doi"] or "").strip()
        hints["open_access_url"] = (
            getattr(work, "open_access_url", None) or hints["open_access_url"] or ""
        ).strip()
        hints["pmcid"] = (getattr(work, "pmcid", None) or hints["pmcid"] or "").strip()
        hints["arxiv_id"] = (getattr(work, "arxiv_id", None) or hints["arxiv_id"] or "").strip()
        src = (getattr(work, "source", None) or "").strip()
        if src:
            hints["provider"] = src

    max_bytes = int(max_file_mb or 50) * 1024 * 1024
    try:
        result = resolve_full_text(
            doi=hints["doi"],
            open_access_url=hints["open_access_url"],
            source_url=hints["source_url"] or hints["open_access_url"],
            pmcid=hints["pmcid"],
            arxiv_id=hints["arxiv_id"],
            provider=hints["provider"],
            db=db,
            max_bytes=max_bytes,
            force=force,
        )
    except Exception as exc:
        logger.warning("uftr resolve failed file_id=%s: %s", getattr(uf, "id", None), exc)
        result = ResolutionResult(
            outcome=FullTextOutcome.NETWORK_ERROR,
            attempts=[
                ResolutionAttempt(
                    resolver="chain",
                    outcome=FullTextOutcome.NETWORK_ERROR,
                    reason="resolve_exception",
                )
            ],
        )

    state = apply_resolution_to_file(uf, result, resolving=False)
    out["fulltext"] = {
        "outcome": state.get("outcome"),
        "user_reason": state.get("user_reason"),
        "full_text_source": state.get("full_text_source"),
        "attempts": state.get("fetch_attempts") or [],
        "last_attempt_at": state.get("last_attempt_at"),
        "found": result.found,
    }

    if not result.found or not result.data:
        out["pdf_error"] = result.outcome.value
        return out

    try:
        applied = apply_pdf_bytes_to_stub(
            db,
            uf,
            data=result.data,
            filename=result.filename or "fulltext.pdf",
            content_type="application/pdf",
            storage=storage,
            upload_dir=upload_dir,
            enqueue_import=enqueue_import,
            user_id=user_id,
            max_file_mb=max_file_mb,
        )
    except Exception as exc:
        logger.warning("uftr attach failed file_id=%s: %s", getattr(uf, "id", None), exc)
        out["pdf_error"] = "oa_attach_exception"
        return out

    if applied.get("ok"):
        out["pdf_attached"] = True
        out["analysis_queued"] = bool(applied.get("queued"))
        # Re-stamp FOUND only after bytes are on the stub (KPI honesty)
        apply_resolution_to_file(uf, result, resolving=False)
        out["fulltext"] = {
            "outcome": result.outcome.value,
            "user_reason": result.user_reason,
            "full_text_source": result.full_text_source,
            "attempts": [a.to_dict() for a in result.attempts],
            "last_attempt_at": state.get("last_attempt_at"),
            "found": True,
        }
    else:
        # Discovery succeeded but storage/attach failed — don't claim FOUND for KPIs
        fail = ResolutionResult(
            outcome=FullTextOutcome.INVALID_RESPONSE,
            attempts=list(result.attempts)
            + [
                ResolutionAttempt(
                    resolver="attach",
                    outcome=FullTextOutcome.INVALID_RESPONSE,
                    reason=str(applied.get("error") or "attach_failed"),
                )
            ],
            full_text_source=result.full_text_source,
            url=result.url,
        )
        state = apply_resolution_to_file(uf, fail, resolving=False)
        out["pdf_error"] = applied.get("error") or "attach_failed"
        out["fulltext"] = {
            "outcome": state.get("outcome"),
            "user_reason": state.get("user_reason"),
            "full_text_source": state.get("full_text_source"),
            "attempts": state.get("fetch_attempts") or [],
            "last_attempt_at": state.get("last_attempt_at"),
            "found": False,
        }
    return out
