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
import json
import logging
import os
import tempfile
import time
import uuid

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from auth.decorators import jwt_required
from backend.ai import ModelError, ModelRegistry, PromptRegistry
from backend.ai.prompts import (
    ANALYSIS_ARRAY_FIELDS,
    ANALYSIS_MAX_CHARS,
    ensure_default_prompts,
)
from imports.registry import extract_text
from quotas.service import QuotaExceededError

from .validation import (
    ValidationError,
    safe_filename,
    validate_extension,
    validate_size,
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
):
    bp = Blueprint("documents", __name__, url_prefix="/api/documents")
    log = logging.getLogger(__name__)

    @bp.route("/upload", methods=["POST"])
    @jwt_required()
    def upload_document():
        user_id = int(g.current_user)

        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"error": "no_file", "message": "No file provided"}), 400

        try:
            ext = validate_extension(f.filename)
        except ValidationError as e:
            return jsonify({"error": e.code, "message": e.message}), 400

        f.stream.seek(0, 2)  # SEEK_END — size without touching disk
        size = f.stream.tell()
        f.stream.seek(0)

        try:
            validate_size(size)
        except ValidationError as e:
            return jsonify({"error": e.code, "message": e.message}), 400

        try:
            quota_service.check_storage_quota(user_id, size)
        except QuotaExceededError as e:
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
            storage_backend.upload(f.stream, key, content_type=f.mimetype)
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
                mime=f.mimetype,
                kind="document",
                path=key,
                size=size,
            )
            db.add(uf)
            db.flush()  # assigns uf.id

            job = UploadJob(
                upload_batch_id=batch.id,
                file_id=uf.id,
                user_id=user_id,
                job_type="import",
                status="pending",
            )
            db.add(job)
            db.flush()  # assigns job.id

            db.add(
                OutboxEvent(
                    aggregate_type="upload_job",
                    aggregate_id=job.id,
                    event_type="job.enqueued",
                    payload=json.dumps({"file_id": uf.id}),
                )
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

    @bp.route("/<int:doc_id>/analysis", methods=["POST"])
    @jwt_required()
    def analyze_document(doc_id):
        """Synchronous counterpart to worker.py's paper_analysis job
        handler — same prompt (by name, reused, not forked — see
        _compose_analysis_text's docstring), same PromptRegistry/
        ModelRegistry/CostLedger path, same array-field normalization.
        Different only in execution context: this runs inline in the
        request instead of via the queue, for a caller that wants the
        result immediately rather than polling a job. Always regenerates
        when called — no content_hash idempotency short-circuit like the
        queue path has, since a caller hitting this endpoint is asking
        for an analysis now, not "only if it doesn't already have one".

        Deliberately does NOT go through PromptBuilder.build() for the
        Task rendering, unlike backend/search/routes.py's rag_answer() —
        evaluated concretely, not skipped for convenience: paper_analysis's
        real template needs both {{ text }} AND {{ max_chars }}, and
        PromptBuilder's variable mapping only ever supplies
        query/question/text (see its own docstring — designed for
        query-style tasks, not document-body ones). Routing this through
        it would render "first  characters" instead of "first 12000
        characters" in the actual prompt sent to the model — a real
        quality regression, not a hypothetical one. What IS adopted here,
        since neither has that downside: model selection via ModelRouter
        (was a fixed injected string) and a PromptExecution audit row
        (was nothing) — both orthogonal to how the Task text gets built."""
        user_id = int(g.current_user)
        db = SessionLocal()
        try:
            uf = db.get(UserFile, doc_id)
            if not uf or uf.user_id != user_id:
                return jsonify({"error": "not_found", "message": "Document not found"}), 404

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

            text = _compose_analysis_text(uf, extracted_text)

            ensure_default_prompts(db)
            prompt_registry = PromptRegistry(db)
            model_registry = ModelRegistry(db)
            model = model_router.get_model_for_task("paper_analysis")
            try:
                prompt, prompt_version = prompt_registry.get_prompt(
                    "paper_analysis",
                    variables={"text": text[:ANALYSIS_MAX_CHARS], "max_chars": ANALYSIS_MAX_CHARS},
                )
            except ValueError as exc:
                return jsonify({"error": "prompt_not_found", "message": str(exc)}), 502

            execution = PromptExecution(
                prompt_version_id=prompt_version.id,
                project_id=uf.project_id,
                user_id=user_id,
                assembled_prompt=prompt,
                status="pending",
            )
            db.add(execution)
            db.commit()

            started = time.perf_counter()
            try:
                result = model_registry.call(
                    model,
                    [{"role": "user", "content": prompt}],
                    user_id=user_id,
                    response_format={"type": "json_object"},
                    prompt_version_id=prompt_version.id,
                )
                data = json.loads(result["content"])
            except ModelError as exc:
                execution.status = "failed"
                db.commit()
                return jsonify({"error": "model_call_failed", "message": str(exc)}), 502
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

            for field in ANALYSIS_ARRAY_FIELDS:
                v = data.get(field)
                if isinstance(v, str):
                    data[field] = [v] if v else []
                elif not isinstance(v, list):
                    data[field] = []
            if not isinstance(data.get("important_terms"), dict):
                data["important_terms"] = {}

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

            return jsonify({"document_id": doc_id, "status": "done", "model": result["model"], "analysis": data}), 200
        finally:
            db.close()

    return bp
