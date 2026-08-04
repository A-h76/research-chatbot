"""Discover routes — OpenAlex + PubMed + arXiv + Europe PMC + ORCID scholarly search/import.

Scholarly imports follow the Golden Rule of Acquisition: when a PDF is available,
attach it and enqueue the shared ``import`` job (→ phase1_analysis → SUE →
evidence → Writing Intelligence), identical to upload. Providers are not special
after bytes are accepted.
"""

from __future__ import annotations

import json

from flask import Blueprint, jsonify, request, session


def create_discover_blueprint(
    *,
    SessionLocal,
    UserFile,
    Project,
    select_fn,
    login_required,
    file_to_dict,
    app_logger,
    feature_flag_service=None,
    discover_flag: str = "discover_search",
    storage=None,
    upload_dir: str | None = None,
    enqueue_import=None,
    max_file_mb: int = 50,
):
    bp = Blueprint("discover_routes", __name__)

    def _flag_blocked_payload():
        """Return error dict if Discover is feature-flagged off, else None."""
        if feature_flag_service is None:
            return None
        uid = session.get("user_id")
        try:
            uid_int = int(uid) if uid is not None else None
        except (TypeError, ValueError):
            uid_int = None
        if feature_flag_service.is_enabled(discover_flag, user_id=uid_int):
            return None
        return {
            "error": "feature_disabled",
            "flag": discover_flag,
            "message": "Discover is temporarily disabled.",
        }

    def _provider_from_request() -> str:
        raw = (
            request.args.get("provider")
            or (request.get_json(silent=True) or {}).get("provider")
            or "openalex"
        )
        p = str(raw or "openalex").strip().lower()
        if p in ("pubmed", "ncbi"):
            return "pubmed"
        if p in ("arxiv", "arXiv"):
            return "arxiv"
        if p in ("europe_pmc", "europepmc", "epmc"):
            return "europe_pmc"
        if p in ("orcid",):
            return "orcid"
        return "openalex"

    def _serialize_work(w) -> dict:
        base = {
            "id": w.id,
            "doi": w.doi,
            "title": w.title,
            "authors": w.authors,
            "year": w.year,
            "venue": w.venue,
            "abstract": w.abstract,
            "citation_count": getattr(w, "citation_count", 0) or 0,
            "open_access_url": w.open_access_url,
            "concepts": list(getattr(w, "concepts", None) or []),
            "source": getattr(w, "source", "") or "",
        }
        src = getattr(w, "source", "") or ""
        if src == "pubmed" or hasattr(w, "pmid"):
            base["pmid"] = getattr(w, "pmid", "") or w.id
            base["pmcid"] = getattr(w, "pmcid", "") or ""
            base["is_open_access"] = bool(getattr(w, "is_open_access", False))
        if src == "arxiv" or hasattr(w, "arxiv_id"):
            base["arxiv_id"] = getattr(w, "arxiv_id", "") or w.id
            base["is_open_access"] = True
            base["primary_category"] = getattr(w, "primary_category", "") or ""
        if src == "europe_pmc" or getattr(w, "source", "") == "europe_pmc":
            base["pmid"] = getattr(w, "pmid", "") or ""
            base["pmcid"] = getattr(w, "pmcid", "") or ""
            base["is_open_access"] = bool(getattr(w, "is_open_access", False))
            base["europe_pmc_id"] = w.id
        if src == "orcid" or getattr(w, "source", "") == "orcid":
            base["orcid_id"] = getattr(w, "orcid_id", "") or ""
            base["put_code"] = getattr(w, "put_code", "") or ""
            base["pmid"] = getattr(w, "pmid", "") or ""
            base["pmcid"] = getattr(w, "pmcid", "") or ""
            base["arxiv_id"] = getattr(w, "arxiv_id", "") or ""
            base["is_open_access"] = bool(getattr(w, "is_open_access", False))
        return base

    @bp.route("/api/discover", methods=["GET"])
    @login_required
    def scholarly_discover():
        from backend.scholarly import provider_enabled

        blocked = _flag_blocked_payload()
        if blocked is not None:
            return jsonify({**blocked, "results": []}), 503

        provider = _provider_from_request()
        if not provider_enabled(provider):
            return (
                jsonify(
                    {
                        "error": "discover_disabled",
                        "message": f"{provider} Discover is temporarily disabled.",
                        "provider": provider,
                        "results": [],
                    }
                ),
                503,
            )

        query = (request.args.get("q") or "").strip()
        if not query:
            return jsonify({"error": "q is required"}), 400
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(20, max(1, int(request.args.get("per_page", 15))))
        db = SessionLocal()
        try:
            if provider == "pubmed":
                from backend.scholarly.pubmed import search_works as pubmed_search

                works = pubmed_search(query, page=page, per_page=per_page, db=db)
            elif provider == "arxiv":
                from backend.scholarly.arxiv import search_works as arxiv_search

                works = arxiv_search(query, page=page, per_page=per_page, db=db)
            elif provider == "europe_pmc":
                from backend.scholarly.europe_pmc import search_works as epmc_search

                works = epmc_search(query, page=page, per_page=per_page, db=db)
            elif provider == "orcid":
                from backend.scholarly.orcid import normalize_orcid_id, search_works as orcid_search

                if not normalize_orcid_id(query):
                    return (
                        jsonify(
                            {
                                "error": "orcid_id_required",
                                "message": "Paste a full ORCID iD (e.g. 0000-0002-1825-0097).",
                                "provider": "orcid",
                                "results": [],
                            }
                        ),
                        400,
                    )
                works = orcid_search(query, page=page, per_page=per_page, db=db)
            else:
                from backend.scholarly.openalex import search_works

                works = search_works(query, page=page, per_page=per_page, db=db)

            return jsonify(
                {
                    "results": [_serialize_work(w) for w in works],
                    "page": page,
                    "per_page": per_page,
                    "provider": provider,
                }
            )
        except Exception as exc:
            app_logger.warning("scholarly_discover failed provider=%s: %s", provider, exc)
            return (
                jsonify(
                    {
                        "error": "discover_unavailable",
                        "message": "Discover is temporarily unavailable.",
                        "provider": provider,
                        "results": [],
                    }
                ),
                503,
            )
        finally:
            db.close()

    def _try_attach_oa_pdf(db, uf, work, *, user_id: int) -> dict:
        """Golden Rule: OA PDF → shared import → SUE → Evidence → Writing Intelligence.

        Provider-specific code ends at PDF bytes. apply_pdf_bytes_to_stub + enqueue_import
        are the same path as upload / Drive / PubMed — no arXiv analysis shortcuts.
        """
        out = {"pdf_attached": False, "analysis_queued": False, "pdf_error": None}
        if storage is None or not upload_dir or enqueue_import is None:
            out["pdf_error"] = "pipeline_not_wired"
            return out
        src = getattr(work, "source", "") or ""
        if (
            not getattr(work, "open_access_url", None)
            and not getattr(work, "pmcid", None)
            and not getattr(work, "arxiv_id", None)
            and src not in ("arxiv",)
        ):
            out["pdf_error"] = "no_oa_pdf"
            return out
        try:
            from backend.library.file_pull import apply_pdf_bytes_to_stub
            from backend.library.sync import has_research_asset

            if has_research_asset(uf):
                out["pdf_error"] = "already_has_pdf"
                return out

            hit = None
            max_b = int(max_file_mb or 50) * 1024 * 1024
            if src == "arxiv" or getattr(work, "arxiv_id", None):
                from backend.scholarly.arxiv import download_pdf

                hit = download_pdf(work, max_bytes=max_b)
            elif src == "europe_pmc":
                from backend.scholarly.europe_pmc import download_open_access_pdf

                hit = download_open_access_pdf(work, max_bytes=max_b)
            elif src == "orcid":
                from backend.scholarly.orcid import download_open_access_pdf

                hit = download_open_access_pdf(work, max_bytes=max_b, db=db)
            else:
                from backend.scholarly.pubmed import download_open_access_pdf

                hit = download_open_access_pdf(work, max_bytes=max_b)
            if not hit:
                out["pdf_error"] = "oa_download_failed"
                return out
            data, filename = hit
            applied = apply_pdf_bytes_to_stub(
                db,
                uf,
                data=data,
                filename=filename,
                content_type="application/pdf",
                storage=storage,
                upload_dir=upload_dir,
                enqueue_import=enqueue_import,
                user_id=user_id,
                max_file_mb=max_file_mb,
            )
            if applied.get("ok"):
                out["pdf_attached"] = True
                out["analysis_queued"] = bool(applied.get("queued"))
            else:
                out["pdf_error"] = applied.get("error") or "attach_failed"
        except Exception as exc:
            app_logger.warning(
                "discover OA attach skipped file_id=%s: %s", getattr(uf, "id", None), exc
            )
            out["pdf_error"] = "oa_attach_exception"
        return out

    @bp.route("/api/discover/import", methods=["POST"])
    @login_required
    def scholarly_discover_import():
        from backend.scholarly import provider_enabled
        from backend.scholarly.crossref import enrich_file_from_doi

        blocked = _flag_blocked_payload()
        if blocked is not None:
            return jsonify(blocked), 503

        body = request.get_json(silent=True) or {}
        provider = str(body.get("provider") or "openalex").strip().lower()
        if provider in ("ncbi",):
            provider = "pubmed"
        if provider in ("europepmc", "epmc"):
            provider = "europe_pmc"
        if provider not in (
            "openalex",
            "pubmed",
            "arxiv",
            "europe_pmc",
            "orcid",
            "discover",
            "related",
        ):
            provider = "openalex"
        if provider in ("discover", "related"):
            search_provider = "openalex"
        else:
            search_provider = provider

        if search_provider == "pubmed":
            if not provider_enabled("pubmed"):
                return (
                    jsonify(
                        {
                            "error": "discover_disabled",
                            "message": "PubMed Discover is temporarily disabled.",
                        }
                    ),
                    503,
                )
        elif search_provider == "arxiv":
            if not provider_enabled("arxiv"):
                return (
                    jsonify(
                        {
                            "error": "discover_disabled",
                            "message": "arXiv Discover is temporarily disabled.",
                        }
                    ),
                    503,
                )
        elif search_provider == "europe_pmc":
            if not provider_enabled("europe_pmc"):
                return (
                    jsonify(
                        {
                            "error": "discover_disabled",
                            "message": "Europe PMC Discover is temporarily disabled.",
                        }
                    ),
                    503,
                )
        elif search_provider == "orcid":
            if not provider_enabled("orcid"):
                return (
                    jsonify(
                        {
                            "error": "discover_disabled",
                            "message": "ORCID Discover is temporarily disabled.",
                        }
                    ),
                    503,
                )
        elif not provider_enabled("openalex"):
            return (
                jsonify(
                    {
                        "error": "discover_disabled",
                        "message": "OpenAlex Discover is temporarily disabled.",
                    }
                ),
                503,
            )

        title = (body.get("title") or "").strip()
        doi = (body.get("doi") or "").strip().removeprefix("https://doi.org/").removeprefix(
            "http://doi.org/"
        )
        authors = (body.get("authors") or "").strip()
        year_raw = body.get("year")
        year = str(year_raw).strip()[:10] if year_raw not in (None, "") else ""
        venue = (body.get("venue") or "").strip()
        abstract = (body.get("abstract") or "").strip()
        open_access_url = (body.get("open_access_url") or "").strip()
        openalex_id = (body.get("openalex_id") or body.get("id") or "").strip()
        pmid = ""
        pmcid = ""
        arxiv_id = ""
        epmc_ext_id = ""
        orcid_id = ""
        put_code = ""
        orcid_ext_id = ""
        if search_provider == "pubmed":
            from backend.scholarly.pubmed import normalize_pmid, normalize_pmcid

            pmid = normalize_pmid(body.get("pmid") or body.get("id") or "")
            pmcid = normalize_pmcid(body.get("pmcid") or "")
            if openalex_id and not pmid:
                pmid = normalize_pmid(openalex_id)
        elif search_provider == "arxiv":
            from backend.scholarly.arxiv import normalize_arxiv_id, pdf_url_for

            arxiv_id = normalize_arxiv_id(
                body.get("arxiv_id") or body.get("id") or openalex_id or ""
            )
            if arxiv_id and not open_access_url:
                open_access_url = pdf_url_for(arxiv_id)
            if not venue:
                venue = "arXiv"
        elif search_provider == "europe_pmc":
            from backend.scholarly.europe_pmc import (
                normalize_europe_pmc_id,
                normalize_pmcid,
                normalize_pmid,
            )

            pmcid = normalize_pmcid(body.get("pmcid") or "")
            pmid = normalize_pmid(body.get("pmid") or "")
            raw_id = normalize_europe_pmc_id(
                body.get("europe_pmc_id") or body.get("id") or openalex_id or ""
            )
            if raw_id and not pmcid and not pmid:
                if normalize_pmcid(raw_id):
                    pmcid = normalize_pmcid(raw_id)
                elif normalize_pmid(raw_id):
                    pmid = normalize_pmid(raw_id)
                else:
                    epmc_ext_id = raw_id
            if pmcid and not epmc_ext_id:
                epmc_ext_id = pmcid
            elif pmid and not epmc_ext_id:
                epmc_ext_id = f"MED:{pmid}"
        elif search_provider == "orcid":
            from backend.scholarly.orcid import (
                external_item_id_for,
                normalize_orcid_id,
                parse_work_id,
            )

            orcid_id = normalize_orcid_id(body.get("orcid_id") or "")
            put_code = str(body.get("put_code") or "").strip()
            parsed_oid, parsed_pc = parse_work_id(body.get("id") or openalex_id or "")
            if parsed_oid and not orcid_id:
                orcid_id = parsed_oid
            if parsed_pc and not put_code:
                put_code = parsed_pc
            pmid = str(body.get("pmid") or "").strip()
            pmcid = str(body.get("pmcid") or "").strip()
            arxiv_id = str(body.get("arxiv_id") or "").strip()
            orcid_ext_id = external_item_id_for(orcid_id, put_code)
        project_id = body.get("project_id")
        import_source = (body.get("import_source") or "discover").strip().lower()
        if import_source not in (
            "discover",
            "related",
            "openalex",
            "pubmed",
            "arxiv",
            "europe_pmc",
            "orcid",
        ):
            import_source = "discover"

        if search_provider == "pubmed":
            if not title and not doi and not pmid:
                return jsonify({"error": "title_doi_or_pmid_required"}), 400
        elif search_provider == "arxiv":
            if not title and not doi and not arxiv_id:
                return jsonify({"error": "title_doi_or_arxiv_id_required"}), 400
        elif search_provider == "europe_pmc":
            if not title and not doi and not pmcid and not pmid and not epmc_ext_id:
                return jsonify({"error": "title_doi_or_europe_pmc_id_required"}), 400
        elif search_provider == "orcid":
            if not orcid_ext_id and not title and not doi:
                return jsonify({"error": "orcid_work_or_title_doi_required"}), 400
        elif not title and not doi:
            return jsonify({"error": "title_or_doi_required"}), 400

        uid = session["user_id"]
        db = SessionLocal()
        try:
            if project_id is not None:
                try:
                    project_id = int(project_id)
                except (TypeError, ValueError):
                    project_id = None
                if project_id is not None:
                    proj = db.get(Project, project_id)
                    if not proj or proj.user_id != uid:
                        return jsonify({"error": "project_not_found"}), 404

            # Dedupe: DOI first, then provider external id
            if doi:
                existing = (
                    db.execute(
                        select_fn(UserFile).where(
                            UserFile.user_id == uid,
                            UserFile.doi == doi,
                        )
                    )
                    .scalars()
                    .first()
                )
                if existing:
                    return jsonify({"already_exists": True, "file": file_to_dict(existing)})

            if search_provider == "pubmed" and pmid:
                existing = (
                    db.execute(
                        select_fn(UserFile).where(
                            UserFile.user_id == uid,
                            UserFile.external_provider == "pubmed",
                            UserFile.external_item_id == pmid,
                        )
                    )
                    .scalars()
                    .first()
                )
                if existing:
                    return jsonify({"already_exists": True, "file": file_to_dict(existing)})

            if search_provider == "arxiv" and arxiv_id:
                existing = (
                    db.execute(
                        select_fn(UserFile).where(
                            UserFile.user_id == uid,
                            UserFile.external_provider == "arxiv",
                            UserFile.external_item_id == arxiv_id,
                        )
                    )
                    .scalars()
                    .first()
                )
                if existing:
                    return jsonify({"already_exists": True, "file": file_to_dict(existing)})

            if search_provider == "europe_pmc" and epmc_ext_id:
                existing = (
                    db.execute(
                        select_fn(UserFile).where(
                            UserFile.user_id == uid,
                            UserFile.external_provider == "europe_pmc",
                            UserFile.external_item_id == epmc_ext_id,
                        )
                    )
                    .scalars()
                    .first()
                )
                if existing:
                    return jsonify({"already_exists": True, "file": file_to_dict(existing)})

            if search_provider == "orcid" and orcid_ext_id:
                existing = (
                    db.execute(
                        select_fn(UserFile).where(
                            UserFile.user_id == uid,
                            UserFile.external_provider == "orcid",
                            UserFile.external_item_id == orcid_ext_id,
                        )
                    )
                    .scalars()
                    .first()
                )
                if existing:
                    return jsonify({"already_exists": True, "file": file_to_dict(existing)})

            # Optional live enrich when client sent thin payload
            pubmed_work = None
            arxiv_work = None
            epmc_work = None
            orcid_work = None
            if search_provider == "pubmed" and pmid:
                try:
                    from backend.scholarly.pubmed import get_work_by_pmid

                    pubmed_work = get_work_by_pmid(pmid, db=db, enrich=True)
                    if pubmed_work:
                        title = title or pubmed_work.title
                        authors = authors or pubmed_work.authors
                        if not year and pubmed_work.year:
                            year = str(pubmed_work.year)
                        venue = venue or pubmed_work.venue
                        doi = doi or pubmed_work.doi
                        abstract = abstract or pubmed_work.abstract
                        open_access_url = open_access_url or pubmed_work.open_access_url
                        pmcid = pmcid or pubmed_work.pmcid
                except Exception as enrich_exc:
                    app_logger.warning("pubmed import enrich skipped: %s", enrich_exc)
                    pubmed_work = None
            elif search_provider == "arxiv" and arxiv_id:
                try:
                    from backend.scholarly.arxiv import get_work_by_id

                    arxiv_work = get_work_by_id(arxiv_id, db=db)
                    if arxiv_work:
                        title = title or arxiv_work.title
                        authors = authors or arxiv_work.authors
                        if not year and arxiv_work.year:
                            year = str(arxiv_work.year)
                        venue = venue or arxiv_work.venue or "arXiv"
                        doi = doi or arxiv_work.doi
                        abstract = abstract or arxiv_work.abstract
                        open_access_url = open_access_url or arxiv_work.open_access_url
                        arxiv_id = arxiv_work.arxiv_id or arxiv_id
                except Exception as enrich_exc:
                    app_logger.warning("arxiv import enrich skipped: %s", enrich_exc)
                    arxiv_work = None
            elif search_provider == "europe_pmc" and (epmc_ext_id or pmcid or pmid):
                try:
                    from backend.scholarly.europe_pmc import (
                        external_item_id_for,
                        get_work_by_id,
                    )

                    epmc_work = get_work_by_id(
                        epmc_ext_id or pmcid or pmid, db=db
                    )
                    if epmc_work:
                        title = title or epmc_work.title
                        authors = authors or epmc_work.authors
                        if not year and epmc_work.year:
                            year = str(epmc_work.year)
                        venue = venue or epmc_work.venue
                        doi = doi or epmc_work.doi
                        abstract = abstract or epmc_work.abstract
                        open_access_url = open_access_url or epmc_work.open_access_url
                        pmcid = pmcid or epmc_work.pmcid
                        pmid = pmid or epmc_work.pmid
                        epmc_ext_id = external_item_id_for(epmc_work) or epmc_ext_id
                except Exception as enrich_exc:
                    app_logger.warning("europe_pmc import enrich skipped: %s", enrich_exc)
                    epmc_work = None
            elif search_provider == "orcid" and orcid_ext_id:
                try:
                    from backend.scholarly.orcid import (
                        enrich_oa_hints,
                        external_item_id_for,
                        get_work_by_id,
                    )

                    orcid_work = get_work_by_id(orcid_ext_id, db=db, enrich=True)
                    if orcid_work:
                        title = title or orcid_work.title
                        authors = authors or orcid_work.authors
                        if not year and orcid_work.year:
                            year = str(orcid_work.year)
                        venue = venue or orcid_work.venue
                        doi = doi or orcid_work.doi
                        abstract = abstract or orcid_work.abstract
                        open_access_url = open_access_url or orcid_work.open_access_url
                        pmid = pmid or orcid_work.pmid
                        pmcid = pmcid or orcid_work.pmcid
                        arxiv_id = arxiv_id or orcid_work.arxiv_id
                        orcid_id = orcid_id or orcid_work.orcid_id
                        put_code = put_code or orcid_work.put_code
                        orcid_ext_id = external_item_id_for(orcid_id, put_code) or orcid_ext_id
                        orcid_work = enrich_oa_hints(orcid_work, db=db)
                        open_access_url = open_access_url or orcid_work.open_access_url
                except Exception as enrich_exc:
                    app_logger.warning("orcid import enrich skipped: %s", enrich_exc)
                    orcid_work = None

            if search_provider == "pubmed":
                display_name = (title or f"PMID:{pmid}" or "pubmed-import")[:300]
                tags = ["from-discover", "from-pubmed"]
                if pmid:
                    tags.append(f"pmid:{pmid}")
                if pmcid:
                    tags.append(f"pmcid:{pmcid}")
                metadata_source = "pubmed"
                external_provider = "pubmed"
                external_item_id = pmid[:120]
            elif search_provider == "arxiv":
                display_name = (title or f"arXiv:{arxiv_id}" or "arxiv-import")[:300]
                tags = ["from-discover", "from-arxiv"]
                if arxiv_id:
                    tags.append(f"arxiv:{arxiv_id}")
                metadata_source = "arxiv"
                external_provider = "arxiv"
                external_item_id = arxiv_id[:120]
            elif search_provider == "europe_pmc":
                display_name = (
                    title or pmcid or (f"PMID:{pmid}" if pmid else "europe-pmc-import")
                )[:300]
                tags = ["from-discover", "from-europe-pmc"]
                if pmcid:
                    tags.append(f"pmcid:{pmcid}")
                if pmid:
                    tags.append(f"pmid:{pmid}")
                metadata_source = "europe_pmc"
                external_provider = "europe_pmc"
                external_item_id = (epmc_ext_id or pmcid or f"MED:{pmid}")[:120]
            elif search_provider == "orcid":
                display_name = (title or f"ORCID:{put_code}" or "orcid-import")[:300]
                tags = ["from-discover", "from-orcid"]
                if orcid_id:
                    tags.append(f"orcid:{orcid_id}")
                if put_code:
                    tags.append(f"put-code:{put_code}")
                metadata_source = "orcid"
                external_provider = "orcid"
                external_item_id = orcid_ext_id[:120]
            else:
                display_name = (title or f"openalex:{openalex_id}" or "openalex-import")[:300]
                tags = ["from-related"] if import_source == "related" else ["from-discover"]
                if openalex_id:
                    if openalex_id.startswith("s2:"):
                        tags.append(openalex_id[:80])
                    else:
                        tags.append(f"openalex:{openalex_id[:80]}")
                metadata_source = "openalex"
                external_provider = ""
                external_item_id = ""

            uf = UserFile(
                user_id=uid,
                project_id=project_id,
                conversation_id=None,
                name=display_name,
                mime="",
                kind="document",
                path="",
                size=0,
                title=(title or display_name)[:500],
                authors=authors[:1000],
                year=year,
                venue=venue[:300],
                doi=doi[:200],
                abstract=abstract[:8000],
                reading_status="unread",
                tags=json.dumps(tags),
                meta_status="done",
                metadata_source=metadata_source,
                source_url=open_access_url[:500],
                doi_verified=False,
                external_provider=external_provider,
                external_item_id=external_item_id,
            )
            db.add(uf)
            db.flush()

            if doi:
                try:
                    enrich_file_from_doi(db, uf.id)
                    db.refresh(uf)
                except Exception as cx_exc:
                    app_logger.warning(
                        "discover import crossref enrich skipped file_id=%s: %s", uf.id, cx_exc
                    )

            attach_meta = {
                "pdf_attached": False,
                "analysis_queued": False,
                "pdf_error": None,
            }
            if search_provider == "pubmed":
                from backend.scholarly.pubmed import PubmedWork

                work_for_pdf = pubmed_work or PubmedWork(
                    id=pmid,
                    pmid=pmid,
                    doi=doi,
                    title=title,
                    open_access_url=open_access_url,
                    pmcid=pmcid,
                    is_open_access=bool(open_access_url or pmcid),
                )
                attach_meta = _try_attach_oa_pdf(db, uf, work_for_pdf, user_id=uid)
                db.refresh(uf)
            elif search_provider == "arxiv":
                from backend.scholarly.arxiv import ArxivWork

                work_for_pdf = arxiv_work or ArxivWork(
                    id=arxiv_id,
                    arxiv_id=arxiv_id,
                    doi=doi,
                    title=title,
                    open_access_url=open_access_url,
                    is_open_access=True,
                )
                attach_meta = _try_attach_oa_pdf(db, uf, work_for_pdf, user_id=uid)
                db.refresh(uf)
            elif search_provider == "europe_pmc":
                from backend.scholarly.europe_pmc import EuropePmcWork

                work_for_pdf = epmc_work or EuropePmcWork(
                    id=epmc_ext_id or pmcid or (f"MED:{pmid}" if pmid else ""),
                    pmid=pmid,
                    pmcid=pmcid,
                    doi=doi,
                    title=title,
                    open_access_url=open_access_url,
                    is_open_access=bool(open_access_url or pmcid),
                )
                attach_meta = _try_attach_oa_pdf(db, uf, work_for_pdf, user_id=uid)
                db.refresh(uf)
            elif search_provider == "orcid":
                from backend.scholarly.orcid import OrcidWork

                work_for_pdf = orcid_work or OrcidWork(
                    id=orcid_ext_id,
                    orcid_id=orcid_id,
                    put_code=put_code,
                    doi=doi,
                    title=title,
                    open_access_url=open_access_url,
                    pmid=pmid,
                    pmcid=pmcid,
                    arxiv_id=arxiv_id,
                    is_open_access=bool(open_access_url or pmcid or arxiv_id),
                )
                attach_meta = _try_attach_oa_pdf(db, uf, work_for_pdf, user_id=uid)
                db.refresh(uf)

            db.commit()
            return (
                jsonify(
                    {
                        "already_exists": False,
                        "file": file_to_dict(uf),
                        "provider": search_provider,
                        **attach_meta,
                    }
                ),
                201,
            )
        except Exception as exc:
            db.rollback()
            app_logger.warning("scholarly_discover_import failed: %s", exc)
            return jsonify({"error": "import_failed"}), 500
        finally:
            db.close()

    return bp
