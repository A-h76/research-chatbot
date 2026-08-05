"""POST /api/documents/upload — a new, Bearer-JWT-authenticated upload
entry point for API clients, alongside the existing session-based
POST /api/files (same relationship as magic-link auth to Google OAuth:
an additional flow, not a replacement — see auth/magic_link.py).

Deliberately reuses the app's existing upload infrastructure rather than
building a parallel one:
  - UserFile (the `files` table) is the file record — no new Document
    model/table. The response still uses the "document_id" key the spec
    asked for; it's just UserFile.id underneath.
  - UploadJob + OutboxEvent, the same transactional-outbox pair
    POST /api/files writes, so the existing queue worker actually picks
    this file up — "processing started" in the response is true.
  - QuotaService (quotas/service.py) for the storage-quota check/record —
    built in an earlier task but never wired into an upload path until
    now.
  - backend.storage's StorageBackend for the object write — this route
    is that abstraction's first real caller.

Constructor-injected (SessionLocal, models, quota_service, storage_backend)
rather than `import server`: server.py runs as __main__, so a module it
reaches into importing "server" back re-executes the whole file under a
second module identity and recurses. Same pattern as every module in
auth/ and quotas/.
"""

import hashlib
import io
import json
import logging
import os
import re
import tempfile
import time
import uuid

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from auth.decorators import jwt_required
from backend.ai import ModelError, ModelRegistry
from backend.ai.prompts import (
    ANALYSIS_ARRAY_FIELDS,
    ANALYSIS_MAX_CHARS,
    PAPER_ANALYSIS_RESPONSE_FORMAT,
    ensure_default_prompts,
    medical_response_format,
)
from backend.jobs.outbox import enqueue_upload_job_with_outbox
from imports.registry import extract_text
from quotas.service import QuotaExceededError

from .validation import (
    DOCUMENT_EXTENSIONS,
    ValidationError,
    kind_for_extension,
    safe_filename,
    validate_upload_bytes,
)


def _compose_analysis_text(uf, extracted_text):
    """Surfaces title/authors/abstract to the model when already known
    (e.g. from a prior extract_metadata pass) by prepending them to the
    same `text` variable the paper_analysis prompt already expects,
    rather than adding them as separate template variables — that would
    mean a second, differently-shaped version of the "paper_analysis"
    prompt competing with the one worker.py's queue handler already
    uses under that exact name, and the two sides' idempotent
    ensure-prompt checks would just keep flipping the active version
    back to what each one expects."""
    header = "\n".join(
        f"{label}: {value}"
        for label, value in (
            ("Title", uf.title),
            ("Authors", uf.authors),
            ("Abstract", uf.abstract),
        )
        if value
    )
    return f"{header}\n\n{extracted_text}" if header else extracted_text


def create_documents_blueprint(
    *,
    SessionLocal,
    UserFile,
    UploadBatch,
    UploadJob,
    OutboxEvent,
    PaperAnalysis,
    PromptExecution,
    quota_service,
    storage_backend,
    model_router,
    ai_gateway=None,
    get_prompt_builder,
    domain_registry,
    AnalysisPipelineResult=None,
    limiter=None,
):
    bp = Blueprint("documents", __name__, url_prefix="/api/documents")
    log = logging.getLogger(__name__)

    def _limit(spec):
        def deco(fn):
            if limiter is None:
                return fn
            return limiter.limit(spec)(fn)

        return deco

    @bp.route("/upload", methods=["POST"])
    @jwt_required()
    @_limit("60 per hour")
    def upload_document():
        user_id = int(g.current_user)

        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"error": "no_file", "message": "No file provided"}), 400

        data = f.read()
        try:
            ext, mime = validate_upload_bytes(
                data, f.filename, allowed=DOCUMENT_EXTENSIONS
            )
        except ValidationError as e:
            log.warning(
                "event=%s filename=%s message=%s",
                e.code,
                f.filename,
                e.message,
            )
            return jsonify({"error": e.code, "message": e.message}), 400

        size = len(data)

        try:
            quota_service.check_storage_quota(user_id, size)
        except QuotaExceededError as e:
            log.warning(
                "event=quota_exceeded kind=storage user_id=%s used=%s limit=%s",
                user_id,
                getattr(e, "used", ""),
                getattr(e, "limit", ""),
            )
            return (
                jsonify(
                    {
                        "error": "storage_quota_exceeded",
                        "message": f"Storage quota exceeded: {e.used + size} bytes "
                        f"would exceed the {e.limit} byte limit",
                    }
                ),
                403,
            )
        except ValueError:
            return jsonify({"error": "not_found", "message": "User not found"}), 404

        filename = safe_filename(f.filename, ext)
        key = f"users/{user_id}/documents/{uuid.uuid4().hex}/{filename}"

        try:
            storage_backend.upload(io.BytesIO(data), key, content_type=mime)
        except Exception:
            return (
                jsonify(
                    {
                        "error": "storage_unavailable",
                        "message": "Could not store the file, try again",
                    }
                ),
                502,
            )

        db = SessionLocal()
        try:
            batch = UploadBatch(user_id=user_id, source="api_documents", file_count=1)
            db.add(batch)
            db.flush()  # assigns batch.id

            uf = UserFile(
                user_id=user_id,
                name=filename[:300],
                mime=mime,
                kind=kind_for_extension(ext),
                path=key,
                size=size,
            )
            db.add(uf)
            db.flush()  # assigns uf.id

            job = enqueue_upload_job_with_outbox(
                db,
                UploadJob=UploadJob,
                OutboxEvent=OutboxEvent,
                user_id=user_id,
                file_id=uf.id,
                job_type="import",
                upload_batch_id=batch.id,
            )

            db.commit()

            # QuotaService owns its own session/transaction (see
            # quotas/service.py) — it can't be folded into the commit
            # above, so it runs after that commit succeeds rather than
            # before. Best-effort like the app's existing AI-usage
            # logging: the file is already safely stored and recorded,
            # so a quota-log hiccup here shouldn't undo the upload or
            # fail the request, only get logged.
            try:
                quota_service.increment_storage(user_id, size)
            except Exception:
                log.warning("quota increment_storage failed for user %s", user_id, exc_info=True)

            return (
                jsonify(
                    {
                        "document_id": uf.id,
                        "status": "PENDING",
                        "message": "Upload successful, processing started",
                    }
                ),
                201,
            )
        except Exception:
            db.rollback()
            try:
                storage_backend.delete(key)
            except Exception:
                pass
            raise
        finally:
            db.close()

    def _clean_metadata(raw):
        """Trims each of title/authors/venue/year and drops empty ones —
        `None`/missing/blank-after-strip all collapse to "not present" so
        PromptBuilder's own `metadata.get(key) or ""` (prompt_builder.py)
        sees a plain missing key rather than an explicit None or a
        run of whitespace."""
        cleaned = {}
        for key in ("title", "authors", "venue", "year"):
            value = raw.get(key)
            if value is None:
                continue
            value = str(value).strip()
            if value:
                cleaned[key] = value
        return cleaned

    @bp.route("/<int:doc_id>/analysis", methods=["POST"])
    @jwt_required()
    @_limit("20 per hour")
    def analyze_document(doc_id):
        """Synchronous counterpart to worker.py's paper_analysis job
        handler — same prompt (by name, reused, not forked — see
        _compose_analysis_text's docstring), same ModelRegistry/CostLedger
        path, same array-field normalization. Different only in execution
        context: this runs inline in the request instead of via the
        queue, for a caller that wants the result immediately rather than
        polling a job. Always regenerates when called — no content_hash
        idempotency short-circuit like the queue path has, since a caller
        hitting this endpoint is asking for an analysis now, not "only if
        it doesn't already have one".

        Now goes through PromptBuilder.build() (get_prompt_builder),
        unlike the version of this route before it — that was evaluated
        and declined at the time because paper_analysis's real template
        needs both {{ text }} and {{ max_chars }}, which PromptBuilder's
        render-variable mapping didn't supply back then. Fixed at the
        source instead of worked around here: prompt_builder.py's
        render_variables now maps {{ text }} to rag_context (not
        user_query) for templates that reference it, and supplies {{
        max_chars }} as len(rag_context) — see that module's own
        docstring. That unblocks routing this endpoint's domain/metadata/
        custom-query support through the same builder every other
        Prompt-Engine-aware route uses, instead of duplicating domain
        injection logic here.

        Optional JSON body: {"domain": str|null, "metadata":
        {"title"|"authors"|"venue"|"year": str|null, ...}, "user_query":
        str|null}. `domain`, if given, must be a real DomainRegistry key —
        this endpoint validates it defensively even though PromptBuilder
        would also raise on a bad domain_prompt_name lookup, since a 400
        with a clear message beats surfacing that as a 500. Pydantic
        wasn't used for this (a genuinely optional call per the task):
        no other route in this codebase validates its body with it
        (backend/upload/validation.py's plain functions are this app's
        existing convention), and four flat fields don't need a schema
        library on top of that."""
        user_id = int(g.current_user)
        body = request.get_json(silent=True) or {}

        domain_from_request = body.get("domain") or None
        if domain_from_request is not None and domain_from_request not in domain_registry.DOMAINS:
            return (
                jsonify(
                    {
                        "error": "invalid_domain",
                        "message": f"Unknown domain {domain_from_request!r}. "
                        f"Valid domains: {sorted(domain_registry.DOMAINS)}",
                    }
                ),
                400,
            )

        metadata_from_request = _clean_metadata(body.get("metadata") or {})
        user_query = (body.get("user_query") or "").strip() or "Analyze this paper"

        db = SessionLocal()
        try:
            uf = db.get(UserFile, doc_id)
            if not uf or uf.user_id != user_id:
                return jsonify({"error": "not_found", "message": "Document not found"}), 404

            # The only pipeline stage this endpoint's own extraction
            # doesn't redo itself (chunking/embedding aside) — if the
            # upload's own "import" job hasn't finished yet, the file may
            # still be mid-write in storage; ask the caller to wait
            # rather than racing it.
            import_job = (
                db.execute(
                    select(UploadJob)
                    .where(UploadJob.file_id == doc_id, UploadJob.job_type == "import")
                    .order_by(UploadJob.id.desc())
                )
                .scalars()
                .first()
            )
            if import_job and import_job.status in ("pending", "running"):
                return (
                    jsonify({"error": "not_ready", "message": "Document content not yet extracted. Please wait."}),
                    409,
                )

            try:
                raw_bytes = storage_backend.download(uf.path)
            except Exception:
                return (
                    jsonify({"error": "storage_unavailable", "message": "Could not read the document"}),
                    502,
                )

            ext = os.path.splitext(uf.name.lower())[1]
            fd, tmp_path = tempfile.mkstemp(suffix=ext)
            try:
                with os.fdopen(fd, "wb") as tmp_f:
                    tmp_f.write(raw_bytes)
                extracted_text = extract_text(tmp_path, uf.mime, uf.name)
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

            no_text = not extracted_text or (extracted_text.startswith("[") and extracted_text.endswith("]"))
            if no_text:
                return (
                    jsonify({"error": "no_text", "message": "No readable text could be extracted from this document"}),
                    422,
                )

            # PdfImporter.extract() (imports/importers/pdf.py) deliberately embeds
            # \x00PAGE<n>\x00 sentinels for chunk_document()'s page-number
            # annotation; the chunking pipeline consumes/strips them, but this
            # route uses the raw extracted text directly and — unlike worker.py's
            # equivalent path, which never persists the full prompt text — stores
            # it in PromptExecution.assembled_prompt below, and Postgres text
            # columns reject embedded NUL bytes outright.
            text = _compose_analysis_text(uf, extracted_text).replace("\x00", "")[:ANALYSIS_MAX_CHARS]

            # Phase 2: consume persisted Phase 1 outputs when available (lazy).
            phase1_context = ""
            domain_from_phase1 = None
            if AnalysisPipelineResult is not None:
                from backend.analysis_pipeline.persistence import load_analysis_result
                from backend.analysis_pipeline.summary import (
                    build_phase1_prompt_context,
                    classification_domain_hint,
                )

                phase1 = load_analysis_result(db, AnalysisPipelineResult, doc_id)
                if phase1 is not None:
                    phase1_context = build_phase1_prompt_context(phase1.phase_results)
                    domain_from_phase1 = classification_domain_hint(phase1.phase_results)

            # Always computed, regardless of an explicit override — this
            # is what the response's "domain_detected" reports, distinct
            # from "domain_used" (see below), which is whatever build()
            # actually applied (the override, if one was given).
            domain_detected = domain_registry.detect_domain(metadata=metadata_from_request, content=text)
            domain_for_build = domain_from_request or domain_from_phase1

            try:
                quota_service.check_token_quota(user_id, len(text) // 4)
            except QuotaExceededError as exc:
                log.warning(
                    "event=quota_exceeded kind=tokens user_id=%s used=%s limit=%s",
                    user_id,
                    getattr(exc, "used", ""),
                    getattr(exc, "limit", ""),
                )
                return (
                    jsonify(
                        {
                            "error": "token_quota_exceeded",
                            "message": f"Monthly token quota exceeded: {exc.used} used of {exc.limit} limit",
                        }
                    ),
                    403,
                )
            except ValueError:
                return jsonify({"error": "not_found", "message": "User not found"}), 404

            ensure_default_prompts(db)
            builder = get_prompt_builder(db)
            try:
                assembled = builder.build(
                    user_query,
                    "paper_analysis",
                    project_id=uf.project_id,
                    user_id=user_id,
                    rag_context=text,
                    domain=domain_for_build,
                    metadata=metadata_from_request,
                    phase1_context=phase1_context or None,
                )
            except ValueError as exc:
                return jsonify({"error": "prompt_not_found", "message": str(exc)}), 400

            model_registry = ModelRegistry(db)
            quality_mode = (body.get("quality_mode") or "balanced").strip().lower()
            confidence = body.get("confidence")
            if confidence is not None:
                try:
                    confidence = float(confidence)
                except (TypeError, ValueError):
                    confidence = None

            execution = PromptExecution(
                prompt_version_id=assembled.prompt_version_id,
                persona_id=assembled.persona_id,
                project_id=uf.project_id,
                user_id=user_id,
                assembled_prompt=assembled.final,
                status="pending",
            )
            db.add(execution)
            db.commit()

            # A domain module's field list is enforced here via a real
            # Structured Outputs schema, not just requested in prose — see
            # backend/ai/prompts.py's medical_response_format() comment for
            # why: plain {"type": "json_object"} mode only guarantees
            # syntactically-valid JSON, and a real call against this exact
            # route returned keys like "17. PICO Extraction (Medical)"
            # instead of the documented field names under it.
            # assembled.document_type (DomainRegistry.detect_document_type(),
            # auto-detected inside build() from this same text/metadata)
            # picks which medical schema variant matches domain_medical's
            # own {% if document_type == ... %} branch for this call.
            response_format = (
                medical_response_format(assembled.document_type)
                if assembled.domain == "medical"
                else PAPER_ANALYSIS_RESPONSE_FORMAT
            )

            started = time.perf_counter()
            try:
                messages = [{"role": "user", "content": assembled.final}]
                from backend.analysis_pipeline.paper_analysis_engine import invoke_paper_analysis_llm

                if ai_gateway is not None:
                    result, ai_provenance = invoke_paper_analysis_llm(
                        ai_gateway=ai_gateway,
                        model_registry=model_registry,
                        messages=messages,
                        user_id=user_id,
                        file_id=int(doc_id),
                        project_id=int(uf.project_id) if uf.project_id is not None else None,
                        quality_mode=quality_mode,
                        confidence=confidence,
                        response_format=response_format,
                        prompt_version_id=assembled.prompt_version_id,
                    )
                else:
                    from backend.ai.capability_router.paper_analysis_resolve import (
                        resolve_paper_analysis_execution,
                    )

                    plan = resolve_paper_analysis_execution(
                        quality_mode=quality_mode,
                        confidence=confidence,
                    )
                    model = plan.model
                    result = model_registry.call(
                        model,
                        messages,
                        user_id=user_id,
                        response_format=response_format,
                        prompt_version_id=assembled.prompt_version_id,
                    )
                    ai_provenance = None
                data = json.loads(result["content"])
            except ModelError as exc:
                execution.status = "failed"
                db.commit()
                log.error("paper analysis model call failed for document %s: %s", doc_id, exc, exc_info=True)
                return jsonify({"error": "model_call_failed", "message": str(exc)}), 500
            except (ValueError, TypeError):
                execution.status = "failed"
                db.commit()
                return (
                    jsonify({"error": "invalid_model_response", "message": "The model did not return valid JSON"}),
                    502,
                )

            execution.status = "success"
            execution.tokens_used = result.get("total_tokens")
            execution.latency_ms = int((time.perf_counter() - started) * 1000)
            db.commit()

            try:
                quota_service.increment_tokens(user_id, result.get("total_tokens") or 0)
            except Exception:
                log.warning("quota increment_tokens failed for user %s", user_id, exc_info=True)

            for field in ANALYSIS_ARRAY_FIELDS:
                v = data.get(field)
                if isinstance(v, str):
                    data[field] = [v] if v else []
                elif not isinstance(v, list):
                    data[field] = []
            if not isinstance(data.get("important_terms"), list):
                data["important_terms"] = []

            content_hash = hashlib.sha256(extracted_text.encode("utf-8", errors="replace")).hexdigest()

            pa = db.execute(select(PaperAnalysis).where(PaperAnalysis.file_id == doc_id)).scalar_one_or_none()
            if pa is None:
                pa = PaperAnalysis(file_id=doc_id, user_id=user_id)
                db.add(pa)
            pa.status = "done"
            pa.content_hash = content_hash
            pa.model = result["model"]
            pa.data = json.dumps(data, ensure_ascii=False)
            pa.error = ""
            db.commit()

            sections_count = len(re.findall(r"^##\s", assembled.final, re.MULTILINE))

            return (
                jsonify(
                    {
                        "analysis": data,
                        "domain_detected": domain_detected,
                        "domain_used": assembled.domain,
                        # No override concept for this one (unlike domain) —
                        # always DomainRegistry.detect_document_type(), so
                        # there's no separate "_detected" vs "_used" pair.
                        "document_type": assembled.document_type,
                        "sections_count": sections_count,
                        "prompt_version_id": assembled.prompt_version_id,
                        "domain_version_id": assembled.domain_version_id,
                        "document_id": doc_id,
                        "phase1_context_used": bool(phase1_context),
                        **(
                            {
                                "ai_execution": (
                                    ai_provenance.get("ai_execution") or ai_provenance
                                )
                            }
                            if ai_provenance
                            else {}
                        ),
                    }
                ),
                200,
            )
        finally:
            db.close()

    return bp
