"""
Personal AI — ChatGPT-style chatbot backend (Phase 1)
Flask + Google OAuth + Postgres/SQLite + OpenAI Responses API (streaming)
+ Projects + selective memory + auto titles + web search
+ File uploads (PDF/Word/image/text) + vision + RAG + citation manager.
"""

import os
import io
import json
import math
import time
import uuid
import shutil
import base64
import binascii
import logging
import threading
from datetime import datetime, timezone, timedelta
from functools import wraps
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

import click
import storage
from flask import (
    Flask,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    render_template,
    Response,
    send_from_directory,
    send_file,
    abort,
    g,
)
from authlib.integrations.flask_client import OAuth
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    select,
    delete,
    func,
    text as sqltext,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from quotas import QuotaService, QuotaExceededError, create_usage_log_model
from openai import OpenAI

# ------------------------------------------------------------------ config
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///chat_dev.db"
if DATABASE_URL.startswith("postgres://"):  # Neon compatibility
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
# DEV_AUTO_LOGIN: set to any non-empty string to skip Google OAuth in development.
# When set, visiting /login automatically signs in as a local dev user.
# NEVER set this in production.
DEV_AUTO_LOGIN = os.environ.get("DEV_AUTO_LOGIN", "")
ALLOWED_EMAILS = [
    e.strip().lower()
    for e in os.environ.get("ALLOWED_EMAILS", "").split(",")
    if e.strip()
]

# Defaults kept to models with confident, verified pricing (see
# backend/ai/cost_ledger.py's PRICING table and its own note on why
# gpt-5-family is deliberately excluded there) — not a claim that gpt-5
# doesn't exist or can't be used; a user can still pick it manually from
# the live-fetched dropdown. Only what's used automatically changed.
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "gpt-4o-mini")
UTILITY_MODEL = os.environ.get("UTILITY_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
FALLBACK_MODELS = [
    m.strip()
    for m in os.environ.get("MODELS", "gpt-4o,gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo").split(",")
    if m.strip()
]

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)  # only used for throwaway temp files now
MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", "25"))

# Optional job-status cache (database-design.md §5's job:{id}:status key).
# Never the source of truth — Postgres's upload_jobs row always is; a
# missing/unreachable Redis just means every read falls through to it.
REDIS_URL = os.environ.get("REDIS_URL", "")
JOB_STATUS_CACHE_TTL_SECONDS = 3600

# Transactional email (provider-agnostic; Resend today). Falls back to console
# logging in development when no API key is configured.
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Personal AI <onboarding@resend.dev>")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "")  # where tickets are routed
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
IS_PRODUCTION = (
    os.environ.get("FLASK_ENV", "").lower() == "production"
    or os.environ.get("APP_ENV", "").lower() == "production"
)
# worker.py's default poll interval is 2s (WORKER_POLL_INTERVAL) and it
# heartbeats every iteration — 60s is ~30 missed cycles, generous enough
# that a normal GC pause or slow job doesn't false-positive as "down".
WORKER_HEALTH_THRESHOLD_SECONDS = int(
    os.environ.get("WORKER_HEALTH_THRESHOLD_SECONDS", "60")
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_MB * 1024 * 1024
# Secure session-cookie defaults (Secure flag only in production/HTTPS).
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
)
client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------------------------------------------------------ JWT (auth/ package)
# Extension alongside session/OAuth login, not a replacement — the
# existing @login_required + session["user_id"] path is untouched. This
# is for future API/programmatic clients that can't hold a browser
# session cookie. JWT_SECRET_KEY defaults to the same secret as Flask
# sessions (inherits the same "set it explicitly in production" caveat
# already flagged for FLASK_SECRET_KEY — production-hardening.md §8 —
# not re-solved here, just not made worse by a second silent fallback).
app.config.update(
    JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", app.secret_key),
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MIN", "15"))
    ),
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    ),
    JWT_ALGORITHM="HS256",
)
from flask_jwt_extended import JWTManager

jwt_manager = JWTManager(app)
from auth import create_jwt, decode_jwt, JWTError, create_get_current_user

# ------------------------------------------------------------------ logging
from observability import (
    configure_logging,
    correlation_id_var,
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    UPLOAD_QUEUE_LENGTH,
    record_ai_call,
    render_metrics,
)

configure_logging()
security_log = logging.getLogger("security")
email_log = logging.getLogger("email")


def log_security_event(event, **fields):
    """Structured audit trail for security-relevant actions."""
    detail = " ".join(f"{k}={v}" for k, v in fields.items())
    security_log.info("event=%s %s", event, detail)


# ------------------------------------------------------------------ email service
class EmailService:
    """Provider-agnostic transactional email. Swap the backend by changing the
    env config, not call sites. In dev (no RESEND_API_KEY) emails are logged to
    the console instead of being sent."""

    def __init__(self, api_key, sender):
        self.api_key = api_key
        self.sender = sender
        self.enabled = bool(api_key)

    def send(self, to, subject, html, text=None, reply_to=None):
        """Returns True if handed off to the provider (or logged in dev)."""
        recipients = [to] if isinstance(to, str) else list(to)
        if not self.enabled:
            email_log.info(
                "[dev email - not sent]\n  to: %s\n  subject: %s\n  body:\n%s",
                ", ".join(recipients),
                subject,
                text or _html_to_text(html),
            )
            return True
        payload = {
            "from": self.sender,
            "to": recipients,
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        if reply_to:
            payload["reply_to"] = reply_to
        try:
            import requests

            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
            if resp.status_code >= 400:
                email_log.error(
                    "Resend error %s: %s", resp.status_code, resp.text[:300]
                )
                return False
            return True
        except Exception as e:
            email_log.error("email send failed: %s", e)
            return False


def _html_to_text(html):
    import re

    return re.sub(r"<[^>]+>", "", html or "").strip()


email_service = EmailService(RESEND_API_KEY, EMAIL_FROM)


# ------------------------------------------------------------------ rate limiting + CSRF
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Opt-in per-route limits (no global throttle so normal chat use is unaffected).
# Uses in-memory storage — switch to redis:// for multi-process production.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
    strategy="fixed-window",
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.before_request
def csrf_protect():
    """Same-origin check for state-changing API calls — defense-in-depth on top
    of SameSite=Lax cookies. Non-browser clients (no Origin/Referer) pass."""
    if request.method in SAFE_METHODS or not request.path.startswith("/api/"):
        return
    src = request.headers.get("Origin") or request.headers.get("Referer")
    if not src:
        return
    src_host = urlparse(src).netloc
    allowed = {request.host, urlparse(APP_BASE_URL).netloc}
    if src_host not in allowed:
        log_security_event("csrf_blocked", path=request.path, origin=src_host)
        return jsonify({"error": "csrf_origin_mismatch"}), 403


_request_log = logging.getLogger("request")


@app.before_request
def _start_request_observability():
    """Correlation id + start time for the logging/metrics after_request
    hook below. Accepts an inbound X-Request-ID so a request can be
    traced across a reverse proxy / calling service, mints one otherwise."""
    g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    correlation_id_var.set(g.request_id)
    g._request_start = time.monotonic()


@app.after_request
def _finish_request_observability(response):
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    # url_rule.rule is the route TEMPLATE ("/api/files/<int:fid>"), not
    # the resolved path — using the resolved path would put every
    # distinct file/conversation/etc. id in its own metric label, an
    # unbounded cardinality that never stops growing.
    route = request.url_rule.rule if request.url_rule else "unmatched"
    duration = time.monotonic() - getattr(g, "_request_start", time.monotonic())
    HTTP_REQUESTS_TOTAL.labels(method=request.method, route=route, status=response.status_code).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, route=route).observe(duration)
    _request_log.info(
        "request",
        extra={
            "method": request.method,
            "route": route,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 1),
        },
    )
    return response


# ------------------------------------------------------------------ dynamic model list
_EXCLUDE = (
    "embedding",
    "whisper",
    "tts",
    "audio",
    "realtime",
    "image",
    "sora",
    "moderation",
    "transcribe",
    "davinci",
    "babbage",
    "instruct",
    "dall-e",
)
_INCLUDE_PREFIX = ("gpt-", "chatgpt-", "o1", "o3", "o4", "chat-latest")
_model_cache = {"ts": 0.0, "models": []}
_model_lock = threading.Lock()

# Model-capability guards for the temperature / reasoning-effort controls.
# Reasoning-only "o"-series models reject `temperature`; reasoning effort is
# only accepted by the "o"-series and gpt-5 families. Re-verify against
# current OpenAI docs if these ever misbehave — single named constants so
# it's a one-line fix.
REASONING_EFFORT_PREFIXES = ("o1", "o3", "o4", "gpt-5")
NO_TEMPERATURE_PREFIXES = ("o1", "o3", "o4")


def supports_reasoning_effort(model):
    return model.startswith(REASONING_EFFORT_PREFIXES)


def supports_temperature(model):
    return not model.startswith(NO_TEMPERATURE_PREFIXES)


def get_models(force=False):
    with _model_lock:
        if (
            not force
            and _model_cache["models"]
            and time.time() - _model_cache["ts"] < 600
        ):
            return _model_cache["models"]
        try:
            raw = client.models.list().data
            models = sorted(
                (
                    m.id
                    for m in raw
                    if m.id.startswith(_INCLUDE_PREFIX)
                    and not any(x in m.id for x in _EXCLUDE)
                ),
                key=lambda mid: next((-m.created for m in raw if m.id == mid), 0),
            )
            if models:
                _model_cache.update(ts=time.time(), models=models)
                return models
        except Exception:
            pass
        return _model_cache["models"] or FALLBACK_MODELS


# ------------------------------------------------------------------ database
Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, nullable=False)
    name = Column(String(200))
    picture = Column(String(500))
    custom_instructions = Column(Text, default="")
    # How this account was first created — 'google' | 'magic' | 'dev'. Set
    # once at creation, never overwritten by a later login via a different
    # method (an existing Google user who later uses a magic link logs
    # into the same account; their auth_provider stays 'google').
    auth_provider = Column(String(20), default="google")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Quotas (quotas/service.py) ──────────────────────────────────────
    # Current storage usage is NOT duplicated here — StorageUsage.bytes_used
    # (below) is already the live, actively-maintained source of truth;
    # only the per-user *limit* is new. Both /api/files and
    # /api/documents/upload check against this same column now (falling
    # back to DEFAULT_STORAGE_LIMIT_BYTES) — they used to disagree, one
    # via the standalone MAX_STORAGE_MB env var (5000 MB default), the
    # other via this column's own default (~1000 MB) — see server.py's
    # upload_file() for why the increment side still doesn't share code
    # despite the check side now agreeing on the same limit.
    storage_limit_bytes = Column(
        BigInteger, default=QuotaService.DEFAULT_STORAGE_LIMIT_BYTES
    )
    monthly_token_used = Column(Integer, default=0)
    monthly_token_limit = Column(Integer, default=QuotaService.DEFAULT_TOKEN_LIMIT)
    quota_reset_at = Column(DateTime, nullable=True)


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    emoji = Column(String(16), default="📁")
    description = Column(Text, default="")  # what this research project is about
    instructions = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    # When set, this is a *paper chat*: retrieval is hard-scoped to this one
    # document and the assistant is told to answer from it alone.
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    title = Column(String(200), default="New chat")
    title_generated = Column(Integer, default=0)
    model = Column(String(100), default=DEFAULT_MODEL)
    temperature = Column(Float, nullable=True)
    reasoning_effort = Column(String(20), nullable=True)
    memory_enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(Text)  # JSON list of web sources
    attachments = Column(Text)  # JSON list [{id,name,mime,kind}]
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    conversation = relationship("Conversation", back_populates="messages")


class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    fact = Column(Text, nullable=False)
    importance = Column(Integer, default=3)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserFile(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    name = Column(String(300), nullable=False)
    mime = Column(String(120))
    kind = Column(String(20))  # image | document
    path = Column(String(500))  # on-disk path
    size = Column(Integer, default=0)
    text_len = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Knowledge Library metadata (v1.0) ──────────────────────────────
    # `name` stays the raw filename; `title` is the extracted paper title so
    # the library can show "Attention Is All You Need" instead of "1706.pdf".
    title = Column(String(500), default="")
    authors = Column(String(1000), default="")  # "Vaswani, A.; Shazeer, N."
    year = Column(String(10), default="")
    venue = Column(String(300), default="")
    doi = Column(String(200), default="")
    abstract = Column(Text, default="")
    reading_status = Column(String(20), default="unread")  # unread|reading|read
    tags = Column(Text, default="[]")  # JSON list[str], user-set
    content_hash = Column(String(64), default="")  # sha256 of extracted text
    meta_status = Column(String(20), default="pending")  # pending|done|failed

    # sha256 of the raw uploaded bytes (not the extracted text) — storage-level
    # identity used for duplicate detection and post-upload integrity checks.
    checksum_sha256 = Column(String(64), nullable=True)

    chunks = relationship("Chunk", cascade="all, delete-orphan", back_populates="file")


class UploadSession(Base):
    """Tracks a presigned/multipart upload between 'client asked for a URL'
    and 'client confirmed the bytes landed' — before a UserFile row exists.
    Expired/abandoned sessions are what garbage collection cleans up."""

    __tablename__ = "upload_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    key = Column(String(300), nullable=False)  # storage object key
    name = Column(String(300), nullable=False)  # original filename
    mime = Column(String(120))
    size_expected = Column(Integer, default=0)
    checksum_sha256 = Column(String(64), nullable=True)  # client-claimed, pre-upload
    upload_id = Column(String(300), nullable=True)  # multipart only
    status = Column(
        String(20), default="pending"
    )  # pending|uploaded|confirmed|expired|aborted
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UploadBatch(Base):
    """Groups files uploaded together in one user action (drag five PDFs
    at once). Nothing creates these yet — today's upload routes handle one
    file per request — so this stays empty until a bulk-upload entry point
    exists; the FK on UploadJob is nullable for exactly that reason."""

    __tablename__ = "upload_batches"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    source = Column(String(20), default="library")  # library|chat_composer|folder_drop
    file_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UploadJob(Base):
    """One row per pipeline stage per file (import | extract_metadata |
    paper_analysis) — the actual queue worker.py polls with FOR UPDATE
    SKIP LOCKED, claims, executes, and marks done/failed. Written by
    upload_file()'s transactional outbox and by worker.py itself when
    chaining follow-on stages — see processing-pipeline-architecture.md."""

    __tablename__ = "upload_jobs"
    id = Column(Integer, primary_key=True)
    upload_batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_type = Column(
        String(30), nullable=False
    )  # import|extract_metadata|paper_analysis
    status = Column(String(20), default="pending")  # pending|running|done|failed
    attempts = Column(Integer, default=0)
    run_after = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )  # due time; backoff pushes this out
    locked_by = Column(Text, nullable=True)
    locked_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    # References pipeline_versions(id) (backend/ai/models.py) — plain
    # column, no ORM-level FK: pipeline_versions has no Python class
    # instantiated anywhere yet (see brain.md §7), so there's no target
    # to point a SQLAlchemy ForeignKey at. migrations/0005 adds the real
    # DB-level FK constraint once that table exists.
    pipeline_version_id = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class StorageUsage(Base):
    """Live per-user storage total — updated in the same transaction as
    every upload/delete, not a periodic rollup, because quota enforcement
    (production-hardening.md §4) needs a synchronous answer before
    accepting a new file, not yesterday's number."""

    __tablename__ = "storage_usage"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    bytes_used = Column(Integer, default=0)
    file_count = Column(Integer, default=0)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


UsageLog = create_usage_log_model(Base)
quota_service = QuotaService(SessionLocal, User, StorageUsage, UsageLog, select)


class ImportSession(Base):
    """Resumable checkpoint for a long-running import — schema only for
    now. Today's extraction is one synchronous pass per file, not the
    step-by-step resumable execution this is designed for; nothing writes
    real checkpoints here until the Step Runner (processing-pipeline-
    architecture.md §5, §10) exists. Created now so that work has a table
    to land in without a later migration."""

    __tablename__ = "import_sessions"
    id = Column(Integer, primary_key=True)
    upload_job_id = Column(
        Integer, ForeignKey("upload_jobs.id"), nullable=False, unique=True
    )
    stage = Column(String(20), default="extract")  # extract|chunk|embed
    checkpoint = Column(Text, default="{}")  # JSON
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OutboxEvent(Base):
    """Transactional outbox: written in the SAME commit as the state
    change it announces (an UploadJob being enqueued), so a Queue Worker
    polling this table never misses an event to a process crash between
    'job row committed' and 'thread started' — the failure mode the old
    threading.Thread(daemon=True) approach had no protection against.
    aggregate_id is polymorphic (aggregate_type says which table it points
    into); no FK, enforced by the writer inserting both rows in one
    transaction, not by the schema."""

    __tablename__ = "outbox_events"
    id = Column(Integer, primary_key=True)
    aggregate_type = Column(String(30), nullable=False)  # 'upload_job' | ...
    aggregate_id = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)  # 'job.enqueued' | ...
    payload = Column(Text, nullable=False)  # JSON
    status = Column(String(20), default="pending")  # pending|dispatched|failed
    dispatched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ModelVersion(Base):
    """Our own versioning of a model choice — so "which model produced
    this row" survives an env var change. Seeded by backfill.py's Task 3
    pass (default_model/utility_model/embed_model, version 1, active)."""

    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True)
    logical_name = Column(String(50), nullable=False)
    provider_model_id = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AIUsageLedger(Base):
    """Append-only cost/usage record — one row per OpenAI call, written
    from the two functions that actually make the calls (responses_text,
    embed_texts), the same choke points research-intelligence.md §7
    designed this around. Currently wired up for the import->embed,
    extract_metadata, and paper_analysis paths only — see worker.py's
    docstring notes for what isn't covered yet (chat, memory extraction,
    titles, compare, gap-finder, writing assistant)."""

    __tablename__ = "ai_usage_ledger"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    upload_job_id = Column(Integer, ForeignKey("upload_jobs.id"), nullable=True)
    kind = Column(String(30), nullable=False)  # embedding|metadata|analysis|...
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)
    # References prompt_versions(id) — no ORM-level FK for the same
    # reason as UploadJob.pipeline_version_id above: prompt_versions has
    # no server.py-registered class (it lives under backend/ai's own
    # private Base). migrations/0006 adds the real DB-level FK.
    prompt_version_id = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class WorkerHeartbeat(Base):
    """Single row (id=1), upserted by worker.py once per poll loop
    iteration — the only signal server.py has that the separate worker.py
    process is actually alive, since it isn't a thread/child process it
    can introspect directly. GET /api/worker/health compares
    last_seen_at against now(); no row at all (id=1 missing) means the
    worker has never run since this table existed."""

    __tablename__ = "worker_heartbeats"
    id = Column(Integer, primary_key=True)
    # timezone=True (-> TIMESTAMPTZ on Postgres), not a bare DateTime:
    # verified live against a real Postgres instance whose session
    # timezone isn't UTC (Asia/Karachi, UTC+5) — writing a UTC-aware
    # datetime into a naive TIMESTAMP column gets silently shifted to the
    # session's zone on write, then misread as if it already were UTC on
    # the way back out, producing a consistent 5-hour skew (a negative
    # age_seconds in GET /api/worker/health). SQLite has no real
    # per-session timezone, so this was invisible there — only showed up
    # once this was actually run against Postgres. The migration
    # (0013_worker_heartbeat.sql) already declared timestamptz correctly;
    # this column just didn't match it. See migrations/0014.
    last_seen_at = Column(DateTime(timezone=True), nullable=False)


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    idx = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    embedding = Column(Text)  # JSON list of floats (null = keyword only)
    # Locators so Paper Chat can cite "p. 4 · §Methodology" rather than just
    # the filename. Nullable: chunks from formats without page structure
    # (and every chunk written by the pre-1.0 code) simply have no locator.
    page = Column(Integer, nullable=True)
    section = Column(String(200), nullable=True)
    file = relationship("UserFile", back_populates="chunks")


class Citation(Base):
    __tablename__ = "citations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    authors = Column(String(500), default="")
    title = Column(String(500), default="")
    year = Column(String(10), default="")
    venue = Column(String(300), default="")  # journal / conference / publisher
    doi = Column(String(200), default="")
    url = Column(String(600), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SupportRequest(Base):
    __tablename__ = "support_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(320), nullable=False)
    subject = Column(String(300), default="")
    category = Column(String(50), default="general")  # bug|feature|general|account
    message = Column(Text, nullable=False)
    status = Column(String(30), default="open")  # open|in_progress|closed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — v1.0 models
# ══════════════════════════════════════════════════════════════════════════


class PaperAnalysis(Base):
    """Cached structured analysis of one paper. One row per file.

    `content_hash` is the SHA-256 of the extracted text: if a document is
    re-uploaded unchanged we reuse the analysis instead of paying for another
    model call. Regeneration happens only when the hash changes or the user
    explicitly asks for a refresh."""

    __tablename__ = "paper_analyses"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending|running|done|failed
    error = Column(Text, default="")
    content_hash = Column(String(64), default="")
    model = Column(String(100), default="")
    data = Column(Text, default="")  # JSON: ANALYSIS_FIELDS
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class DerivedAnalysis(Base):
    """Cached multi-paper output — comparison ('compare') or gap analysis
    ('gaps'). Keyed by a hash of the sorted file-id set so the same selection
    never regenerates."""

    __tablename__ = "derived_analyses"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    kind = Column(String(20), nullable=False)  # compare|gaps
    selection_hash = Column(String(64), nullable=False)
    file_ids = Column(Text, default="[]")  # JSON list[int]
    data = Column(Text, default="")  # JSON
    model = Column(String(100), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)  # paper note
    title = Column(String(300), default="")
    content = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SearchIndex(Base):
    """Unified semantic index over notes, citations and chat messages.

    Papers are NOT indexed here — their `Chunk` rows already carry embeddings
    and are searched directly, which keeps a single source of truth per
    document and avoids duplicating a paper's vectors."""

    __tablename__ = "search_index"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    kind = Column(String(20), nullable=False)  # note|citation|chat
    ref_id = Column(Integer, nullable=False)  # id in the source table
    title = Column(String(400), default="")
    snippet = Column(Text, default="")
    embedding = Column(Text)  # JSON list[float] | null
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# checkfirst=True is SQLAlchemy's own default (verified: MetaData.create_all's
# signature already defaults to it) — spelled out explicitly so it's not
# a fact a reader has to already know. It's what makes this call safe to
# run after migrations/*.sql already created these same tables: it only
# creates what's missing, never re-creates or errors on what exists.
Base.metadata.create_all(engine, checkfirst=True)


def ensure_columns():
    """Lightweight migrations for DBs created by a previous version.

    Each statement is attempted independently and failures are swallowed —
    "duplicate column" is the expected outcome on an already-migrated DB.
    Every column added here is nullable or has a default, so old rows stay
    valid and the app keeps working without a backfill step."""
    for stmt in (
        # ── pre-1.0 ────────────────────────────────────────────────────
        "ALTER TABLE messages ADD COLUMN attachments TEXT",
        "ALTER TABLE users ADD COLUMN custom_instructions TEXT",
        "ALTER TABLE memories ADD COLUMN importance INTEGER DEFAULT 3",
        "ALTER TABLE conversations ADD COLUMN temperature FLOAT",
        "ALTER TABLE conversations ADD COLUMN reasoning_effort VARCHAR(20)",
        "ALTER TABLE conversations ADD COLUMN memory_enabled INTEGER DEFAULT 1",
        # ── Research Workspace v1.0 ────────────────────────────────────
        "ALTER TABLE projects ADD COLUMN description TEXT",
        "ALTER TABLE conversations ADD COLUMN file_id INTEGER",
        "ALTER TABLE files ADD COLUMN title VARCHAR(500)",
        "ALTER TABLE files ADD COLUMN authors VARCHAR(1000)",
        "ALTER TABLE files ADD COLUMN year VARCHAR(10)",
        "ALTER TABLE files ADD COLUMN venue VARCHAR(300)",
        "ALTER TABLE files ADD COLUMN doi VARCHAR(200)",
        "ALTER TABLE files ADD COLUMN abstract TEXT",
        "ALTER TABLE files ADD COLUMN reading_status VARCHAR(20) DEFAULT 'unread'",
        "ALTER TABLE files ADD COLUMN tags TEXT DEFAULT '[]'",
        "ALTER TABLE files ADD COLUMN content_hash VARCHAR(64)",
        "ALTER TABLE files ADD COLUMN meta_status VARCHAR(20) DEFAULT 'pending'",
        "ALTER TABLE chunks ADD COLUMN page INTEGER",
        "ALTER TABLE chunks ADD COLUMN section VARCHAR(200)",
        # ── Storage architecture ───────────────────────────────────────
        "ALTER TABLE files ADD COLUMN checksum_sha256 VARCHAR(64)",
        "ALTER TABLE upload_jobs ADD COLUMN run_after TIMESTAMP",
        "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20) DEFAULT 'google'",
        "ALTER TABLE users ADD COLUMN storage_limit_bytes BIGINT DEFAULT 1000000000",
        "ALTER TABLE users ADD COLUMN monthly_token_used INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN monthly_token_limit INTEGER DEFAULT 100000",
        "ALTER TABLE users ADD COLUMN quota_reset_at TIMESTAMP",
        # ── ORM/migration drift found while fixing run_migrations.py:
        # these columns were in migrations/0002 and 0006 but never made
        # it into the UploadJob/AIUsageLedger classes above, so a
        # SQLite dev DB (which only ever runs the ORM's create_all, never
        # migrations/*.sql) was permanently missing them.
        "ALTER TABLE upload_jobs ADD COLUMN locked_by TEXT",
        "ALTER TABLE upload_jobs ADD COLUMN locked_at TIMESTAMP",
        "ALTER TABLE upload_jobs ADD COLUMN pipeline_version_id INTEGER",
        "ALTER TABLE ai_usage_ledger ADD COLUMN prompt_version_id INTEGER",
    ):
        try:
            with engine.begin() as conn:
                conn.execute(sqltext(stmt))
        except Exception:
            pass

    # Indexes for the new access patterns (library listing, cache lookups,
    # semantic search). CREATE INDEX IF NOT EXISTS works on both SQLite and
    # Postgres, so this is safe to run on every boot.
    for stmt in (
        "CREATE INDEX IF NOT EXISTS ix_files_user ON files (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_chunks_file ON chunks (file_id)",
        "CREATE INDEX IF NOT EXISTS ix_notes_user ON notes (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_paper_analyses_file ON paper_analyses (file_id)",
        "CREATE INDEX IF NOT EXISTS ix_derived_sel ON derived_analyses (user_id, kind, selection_hash)",
        "CREATE INDEX IF NOT EXISTS ix_search_index_user ON search_index (user_id, kind)",
        "CREATE INDEX IF NOT EXISTS ix_files_user_checksum ON files (user_id, checksum_sha256)",
        "CREATE INDEX IF NOT EXISTS ix_upload_sessions_user ON upload_sessions (user_id)",
        # ── Storage foundation (database-design.md) ─────────────────────
        # ix_upload_batches_user and ix_outbox_events_pending must match
        # migrations 0001/0007's definitions exactly (column list / WHERE
        # clause), not just the name — Postgres's CREATE INDEX IF NOT
        # EXISTS only checks the name, so if this ran first with a lesser
        # definition, the migration's more complete one would silently
        # never get created (same name = skipped), not just redundantly
        # re-created. Found by actually comparing both files side by
        # side, not assumed.
        "CREATE INDEX IF NOT EXISTS ix_upload_batches_user ON upload_batches (user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_upload_jobs_file ON upload_jobs (file_id)",
        "CREATE INDEX IF NOT EXISTS ix_upload_jobs_batch ON upload_jobs (upload_batch_id)",
        "CREATE INDEX IF NOT EXISTS ix_upload_jobs_user_status ON upload_jobs (user_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_outbox_events_pending ON outbox_events (status, created_at) WHERE status = 'pending'",
        "CREATE INDEX IF NOT EXISTS ix_usage_logs_user ON usage_logs (user_id, created_at)",
    ):
        try:
            with engine.begin() as conn:
                conn.execute(sqltext(stmt))
        except Exception:
            pass


ensure_columns()

# ------------------------------------------------------------------ auth
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "not_authenticated"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)

    return wrapper


@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect("/")

    # ── DEV_AUTO_LOGIN bypass ─────────────────────────────────────────────────
    # When DEV_AUTO_LOGIN is set (development only), automatically create and
    # sign in a local dev account so you can work without Google OAuth.
    if DEV_AUTO_LOGIN:
        db = SessionLocal()
        try:
            dev_email = "dev@localhost"
            user = db.execute(
                select(User).where(User.email == dev_email)
            ).scalar_one_or_none()
            if not user:
                user = User(
                    email=dev_email, name="Dev User", picture="", auth_provider="dev"
                )
                db.add(user)
                db.commit()
            session["user_id"] = user.id
            session["user_email"] = user.email
            access, refresh = create_jwt(user.id)
            session["jwt"] = {"access": access, "refresh": refresh}
        finally:
            db.close()
        return redirect("/")
    # ─────────────────────────────────────────────────────────────────────────

    return render_template(
        "login.html",
        oauth_ready=bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        error=None,
    )


@app.route("/auth/google")
def auth_google():
    redirect_uri = url_for("auth_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    token = google.authorize_access_token()
    info = token.get("userinfo") or {}
    email = (info.get("email") or "").lower()
    if not email:
        return (
            render_template(
                "login.html",
                oauth_ready=True,
                error="Could not read your Google account email.",
            ),
            403,
        )
    if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
        return (
            render_template(
                "login.html",
                oauth_ready=True,
                error="Access denied — this account is not allowed.",
            ),
            403,
        )
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user:
            user = User(email=email, auth_provider="google")
            db.add(user)
        user.name = info.get("name") or email
        user.picture = info.get("picture") or ""
        db.commit()
        session["user_id"] = user.id
        session["user_email"] = user.email
        # Extra capability alongside the session, not a replacement for
        # it — API/programmatic clients that can't hold a browser cookie
        # can pick this up via GET /api/auth/jwt once the user has a
        # session; nothing about the redirect/session flow above changed.
        access, refresh = create_jwt(user.id)
        session["jwt"] = {"access": access, "refresh": refresh}
    finally:
        db.close()
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/api/dev-login", methods=["POST"])
def dev_login():
    """Sign in as the local dev user without Google OAuth.

    Only works when DEV_AUTO_LOGIN is set in the environment.
    Returns 403 in production / when DEV_AUTO_LOGIN is not set.
    """
    if not DEV_AUTO_LOGIN:
        return (
            jsonify(
                {
                    "error": "dev_login_disabled",
                    "detail": "Set DEV_AUTO_LOGIN=1 in your .env file to use this endpoint.",
                }
            ),
            403,
        )
    db = SessionLocal()
    try:
        dev_email = "dev@localhost"
        user = db.execute(
            select(User).where(User.email == dev_email)
        ).scalar_one_or_none()
        if not user:
            user = User(email=dev_email, name="Dev User", picture="")
            db.add(user)
            db.commit()
        session["user_id"] = user.id
        session["user_email"] = user.email
        access, refresh = create_jwt(user.id)
        session["jwt"] = {"access": access, "refresh": refresh}
        return jsonify({"ok": True, "user_id": user.id})
    finally:
        db.close()


# Magic-link auth — a third login method (session-based, same shape as
# Google OAuth/dev-login), not a replacement for either. Built via a
# factory taking explicit dependencies rather than `import server` inside
# auth/magic_link.py — this file is normally run directly as __main__, so
# a module named "server" importing "server" back would re-execute this
# whole file under a second module identity and recurse. See
# auth/magic_link.py's module docstring for the full explanation.
from auth.magic_link import create_magic_link_blueprint

app.register_blueprint(
    create_magic_link_blueprint(
        secret_key=app.secret_key,
        limiter=limiter,
        email_service=email_service,
        SessionLocal=SessionLocal,
        User=User,
        select=select,
        ALLOWED_EMAILS=ALLOWED_EMAILS,
        APP_BASE_URL=APP_BASE_URL,
        create_jwt=create_jwt,
        log_security_event=log_security_event,
    )
)

# POST /api/documents/upload — Bearer-JWT-authenticated upload entry point
# alongside the existing session-based POST /api/files. Reuses UserFile/
# UploadJob/OutboxEvent (no new Document model) and quota_service — see
# backend/upload/routes.py's module docstring for the full reasoning.
from backend.upload.validation import MAX_DOCUMENT_UPLOAD_MB
from backend.upload.routes import create_documents_blueprint
from backend.storage import get_storage_backend

# Flask rejects an over-limit request body before any route code runs —
# this route's own limit must not be shadowed by the app-wide one.
app.config["MAX_CONTENT_LENGTH"] = (
    max(MAX_FILE_MB, MAX_DOCUMENT_UPLOAD_MB) * 1024 * 1024
)
app.register_blueprint(
    create_documents_blueprint(
        SessionLocal=SessionLocal,
        UserFile=UserFile,
        UploadBatch=UploadBatch,
        UploadJob=UploadJob,
        OutboxEvent=OutboxEvent,
        PaperAnalysis=PaperAnalysis,
        quota_service=quota_service,
        storage_backend=get_storage_backend(),
        utility_model=UTILITY_MODEL,
    )
)

# GET /api/documents/search, POST /api/rag — Bearer-JWT counterparts to
# the existing session-based POST /api/search (below), same relationship
# as /api/documents/upload has to /api/files. Search the exact same
# Chunk.embedding data /api/search already uses for papers — see
# backend/search/routes.py's module docstring for why this isn't a
# second search engine.
from backend.search.routes import create_search_blueprint

app.register_blueprint(
    create_search_blueprint(
        SessionLocal=SessionLocal,
        UserFile=UserFile,
        Chunk=Chunk,
        utility_model=UTILITY_MODEL,
    )
)

# Unified user lookup — session first, Bearer JWT second, None if
# neither. A helper for routes that should accept either auth method;
# @login_required (session-only) and @jwt_required() (JWT-only, from
# auth/decorators.py) are both untouched and still the right choice for
# routes that should accept exactly one.
get_current_user = create_get_current_user(SessionLocal, User)


# ══════════════════════════════════════════════════════════════════════════
# JWT — extra capability alongside session/OAuth login, for API/programmatic
# clients that can't hold a browser cookie. Neither route below touches the
# session-based login flow above.
#
# Not built: a headless OAuth-code-exchange endpoint (a client does its own
# Google OAuth, hands us the raw code, we exchange it for a JWT without a
# browser session ever existing). Nothing in this project is a headless
# client today — no CLI, no mobile app — building that integration surface
# ahead of an actual consumer is exactly the kind of speculative work this
# project's own docs (upload-architecture.md §11 on Feature Flags, among
# others) have consistently deferred until there's a real one.
# ══════════════════════════════════════════════════════════════════════════


@app.route("/api/auth/jwt")
@login_required
def get_session_jwt():
    """For a client that already has the browser session (just logged in
    via Google OAuth) and wants a portable Bearer token instead. Returns
    the token minted at login if it's still valid; mints a fresh one
    (access tokens are short-lived by design — 15 min default) if
    the session doesn't have one yet or it's expired — a client calling
    this should never get back something already broken."""
    stored = session.get("jwt")
    if stored:
        try:
            decode_jwt(stored["access"])
            return jsonify(
                {"access_token": stored["access"], "refresh_token": stored["refresh"]}
            )
        except JWTError:
            pass  # expired/invalid — fall through and mint a fresh pair
    access, refresh = create_jwt(session["user_id"])
    session["jwt"] = {"access": access, "refresh": refresh}
    return jsonify({"access_token": access, "refresh_token": refresh})


@app.route("/api/auth/token", methods=["POST"])
def refresh_jwt():
    """Exchange a refresh token for a new access token. The email+password
    variant of this endpoint doesn't apply — this app has no password-based
    accounts, only Google OAuth — so this covers just the refresh_token
    grant, which every client holding a JWT eventually needs regardless of
    how the original token was issued."""
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return jsonify({"error": "refresh_token_required"}), 400
    try:
        claims = decode_jwt(refresh_token)
    except JWTError:
        return jsonify({"error": "invalid_refresh_token"}), 401
    if claims.get("type") != "refresh":
        return (
            jsonify(
                {"error": "invalid_refresh_token", "detail": "not a refresh token"}
            ),
            401,
        )
    try:
        user_id = int(claims.get("sub"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_refresh_token"}), 401

    db = SessionLocal()
    try:
        # A refresh token survives account deletion unless checked here —
        # don't mint new access tokens for a user that no longer exists.
        if not db.get(User, user_id):
            return jsonify({"error": "invalid_refresh_token"}), 401
    finally:
        db.close()

    access, new_refresh = create_jwt(user_id)
    return jsonify({"access_token": access, "refresh_token": new_refresh})


@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")


# ══════════════════════════════════════════════════════════════════════════
# AI layer (backend/ai/) — prompt registry, multi-provider model registry,
# cost ledger. get_prompt_registry()/get_model_registry() are request-scoped
# factories, NOT instances built once at startup: PromptRegistry/ModelRegistry
# each hold one open SQLAlchemy Session for their lifetime (their own
# constructors take a Session instance, not a factory) — sharing one across
# concurrent requests would be a real bug, not a style issue. Every other
# route in this file already opens/closes its own `db = SessionLocal()` per
# request; these two follow that same convention rather than introducing
# Flask's g/app.extensions for just this one feature. CostLedger is the one
# genuine startup-time singleton here — it holds no session at all
# (estimate_cost() is pure; log() takes a session as a call argument).
#
# prompt_versions/pipeline_versions/model_registry_cost_ledger only exist
# under backend/ai's own private declarative Bases, never server.py's — see
# prompt_registry.py's and model_registry.py's own docstrings for why. This
# project has no Alembic (migrations/*.sql are hand-written, run via
# run_migrations.py — 00-constitution.md), so there's no autogenerate step
# to feed; what actually matters is these tables existing before anything
# queries them. checkfirst=True is a no-op everywhere the real Postgres
# migration already ran — it only creates anything on a fresh SQLite dev DB
# (verified: prompt_versions/pipeline_versions didn't exist there before this).
# ══════════════════════════════════════════════════════════════════════════
from backend.ai import PromptRegistry, ModelRegistry, CostLedger, ModelError, TemplateError
from backend.ai.prompt_registry import _Base as _ai_prompt_base
from backend.ai.model_registry import _Base as _ai_model_base, CostLedgerEntry as _CostLedgerEntry

_ai_prompt_base.metadata.create_all(engine, checkfirst=True)
_ai_model_base.metadata.create_all(engine, checkfirst=True)

_cost_ledger = CostLedger(_CostLedgerEntry)


def get_prompt_registry(db_session):
    return PromptRegistry(db_session)


def get_model_registry(db_session):
    return ModelRegistry(db_session)


def get_cost_ledger():
    return _cost_ledger


@app.route("/metrics")
def metrics():
    """Unauthenticated, same reasoning as /api/worker/health right below
    — a Prometheus scrape target, not a user-facing route. Firewall it at
    the network/reverse-proxy level in a real deploy rather than gating
    it behind app auth, same as any standard Prometheus setup."""
    db = SessionLocal()
    try:
        for status in ("pending", "running", "failed", "done"):
            count = db.execute(
                select(func.count()).select_from(UploadJob).where(UploadJob.status == status)
            ).scalar_one()
            UPLOAD_QUEUE_LENGTH.labels(status=status).set(count)
    finally:
        db.close()
    return Response(render_metrics(), mimetype="text/plain; version=0.0.4")


@app.route("/api/worker/health")
def worker_health():
    """Unauthenticated on purpose — an ops liveness check (uptime monitor,
    orchestrator probe), not a user-facing route, same class as a plain
    /healthz. Reports on worker.py specifically, not this Flask process:
    server.py being up says nothing about whether the separate worker.py
    process is still polling upload_jobs."""
    db = SessionLocal()
    try:
        hb = db.get(WorkerHeartbeat, 1)
    finally:
        db.close()

    if hb is None:
        return jsonify({
            "status": "unknown",
            "message": "worker has not reported in since this deploy — "
                       "either it has never run, or it started before this "
                       "endpoint existed",
        }), 503

    last_seen = hb.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - last_seen).total_seconds()
    healthy = age_seconds <= WORKER_HEALTH_THRESHOLD_SECONDS

    return jsonify({
        "status": "ok" if healthy else "down",
        "last_seen_at": hb.last_seen_at.isoformat(),
        "age_seconds": round(age_seconds, 1),
        "threshold_seconds": WORKER_HEALTH_THRESHOLD_SECONDS,
    }), (200 if healthy else 503)


@app.route("/api/ai/prompts")
@login_required
def list_ai_prompts():
    db = SessionLocal()
    try:
        registry = get_prompt_registry(db)
        prompts = registry.list_prompts()
        return jsonify({"prompts": [
            {"name": p.name, "version": p.version, "template": p.template,
             "is_active": p.is_active,
             "created_at": p.created_at.isoformat() if p.created_at else None}
            for p in prompts
        ]})
    finally:
        db.close()


@app.route("/api/ai/test", methods=["POST"])
@login_required
def test_ai_call():
    """Dev-only: exercises ModelRegistry.call() directly against a real
    provider. Gated on IS_PRODUCTION — "optional, for dev" shouldn't mean
    an unrestricted call-any-model-with-any-prompt endpoint shipped without
    a guard; that's a real cost/abuse surface, not just a nicety to skip."""
    if IS_PRODUCTION:
        return jsonify({"error": "disabled_in_production"}), 403

    data = request.get_json(silent=True) or {}
    model = data.get("model") or DEFAULT_MODEL
    message = data.get("message") or "Say hello in one short sentence."

    db = SessionLocal()
    try:
        registry = get_model_registry(db)
        result = registry.call(
            model, [{"role": "user", "content": message}],
            user_id=session["user_id"], max_tokens=data.get("max_tokens", 100))
        return jsonify(result)
    except ModelError as exc:
        return jsonify({"error": "model_call_failed", "message": str(exc)}), 502
    finally:
        db.close()


# ------------------------------------------------------------------ text extraction / chunking / embeddings

# extract_text(path, mime, name) -> str: '' = no readable text, '[...]' =
# a bracketed note (unsupported/unparseable format), or the extracted
# text. Implemented by the Import Engine (imports/) — one Importer class
# per format behind a registry, replacing what used to be an if/elif
# chain of _extract_pdf/_extract_docx/etc. functions in this file.
from imports import extract_text


def pdf_page_images(path, max_pages=6, zoom=2.0):
    """Rasterise the first pages of a PDF to PNG data-URLs (for scanned PDFs
    with no text layer, so the vision model can still read them)."""
    import fitz  # PyMuPDF

    urls = []
    doc = fitz.open(path)
    try:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            b64 = base64.b64encode(pix.tobytes("png")).decode()
            urls.append(f"data:image/png;base64,{b64}")
    finally:
        doc.close()
    return urls


def chunk_text(text, size=1500, overlap=200):
    """Legacy plain-text chunker kept for non-document paths (pptx, xlsx,
    zip members, raw text).  Returns list[str] with no locators."""
    text = text.strip()
    if not text:
        return []
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += size - overlap
    return chunks[:400]


import re as _re

_PAGE_RE = _re.compile(r"\x00PAGE(\d+)\x00")
_SEC_RE = _re.compile(r"\x00SEC\d+:([^\x00]*)\x00")


def chunk_document(text, size=1500, overlap=200):
    """Sentinel-aware chunker for PDFs and DOCX files.

    Returns list[dict] with keys:
      content  – clean text, no sentinels
      page     – int | None  (1-based page number for PDFs)
      section  – str | None  (heading text for DOCX)

    Algorithm
    ---------
    1. Walk the text character-by-character tracking the *current* page and
       section from any sentinel we pass.
    2. Strip all sentinels from the content so the model never sees them.
    3. Slide a window of `size` characters (with `overlap`) over the clean
       text, attaching the page/section that was active when that slice
       started.
    """
    if not text:
        return []

    # ── pass 1: build a sentinel-stripped clean text plus a position map ──
    # pos_map[clean_pos] = (page, section) at the time we wrote that char
    clean_chars = []
    pos_meta = []  # parallel list: meta at each clean char position
    cur_page = None
    cur_section = None
    idx = 0
    n = len(text)

    while idx < n:
        # Check for sentinel starting here
        page_m = _PAGE_RE.match(text, idx)
        sec_m = _SEC_RE.match(text, idx)
        if page_m:
            cur_page = int(page_m.group(1))
            idx = page_m.end()
            continue
        if sec_m:
            cur_section = sec_m.group(1).strip()
            idx = sec_m.end()
            continue
        ch = text[idx]
        clean_chars.append(ch)
        pos_meta.append((cur_page, cur_section))
        idx += 1

    clean = "".join(clean_chars).strip()
    if not clean:
        return []

    # ── pass 2: sliding window over clean text ──
    chunks = []
    i = 0
    total = len(clean)
    while i < total:
        end = min(i + size, total)
        page, section = pos_meta[i] if i < len(pos_meta) else (None, None)
        chunks.append(
            {
                "content": clean[i:end],
                "page": page,
                "section": section,
            }
        )
        i += size - overlap

    return chunks[:400]  # safety cap


def embed_texts(texts, user_id=None):
    """Returns list of embeddings or None per text (None = embedding failed).

    `user_id`: when given, logs token usage to ai_usage_ledger (kind=
    "embedding") — optional so existing call sites that don't have a
    user_id handy (or don't need cost tracking) are unaffected."""
    try:
        out = []
        total_tokens = 0
        for i in range(0, len(texts), 64):
            resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i : i + 64])
            out.extend([d.embedding for d in resp.data])
            total_tokens += getattr(resp.usage, "prompt_tokens", 0) or 0
        record_ai_call(EMBED_MODEL, prompt_tokens=total_tokens)
        if user_id:
            _log_ai_usage(user_id, "embedding", "embed_model", total_tokens, 0)
        return out
    except Exception:
        return [None] * len(texts)


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return dot / (na * nb)


def keyword_score(query, text):
    q = set(w for w in query.lower().split() if len(w) > 3)
    if not q:
        return 0.0
    t = text.lower()
    return sum(1 for w in q if w in t) / len(q)


def rag_retrieve(user_id, conversation_id, project_id, query, top_k=6, file_id=None):
    """Top chunks from files scoped to this conversation or its project.

    When file_id is given the retrieval is hard-scoped to that single file —
    used by Paper Chat (M7) so the AI draws only from the paper being discussed.
    """
    db = SessionLocal()
    try:
        if file_id:
            # Hard-scope: retrieve only from the specified paper
            files = (
                db.execute(
                    select(UserFile).where(
                        UserFile.id == file_id,
                        UserFile.user_id == user_id,
                    )
                )
                .scalars()
                .all()
            )
        else:
            files = (
                db.execute(select(UserFile).where(UserFile.user_id == user_id))
                .scalars()
                .all()
            )
            files = [
                f
                for f in files
                if (f.conversation_id == conversation_id)
                or (project_id and f.project_id == project_id)
            ]
        if not files:
            return []
        fids = [f.id for f in files]
        fnames = {f.id: f.name for f in files}
        chunks = (
            db.execute(select(Chunk).where(Chunk.file_id.in_(fids))).scalars().all()
        )
        if not chunks:
            return []
        q_emb = embed_texts([query])[0]
        scored = []
        for c in chunks:
            if q_emb and c.embedding:
                try:
                    s = cosine(q_emb, json.loads(c.embedding))
                except Exception:
                    s = keyword_score(query, c.content)
            else:
                s = keyword_score(query, c.content)
            scored.append((s, c))
        scored.sort(key=lambda x: -x[0])
        results = []
        for s, c in scored[:top_k]:
            if s <= 0:
                continue
            entry = {
                "file": fnames.get(c.file_id, "file"),
                "content": c.content[:2000],
            }
            # Attach locators when present so the model can cite specifically
            # (e.g. "p. 7, §Methodology") rather than just the filename.
            if c.page is not None:
                entry["page"] = c.page
            if c.section:
                entry["section"] = c.section
            results.append(entry)
        return results
    finally:
        db.close()


# ------------------------------------------------------------------ web search
def web_search(query, max_results=5):
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    out = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                out.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href") or r.get("url", ""),
                        "snippet": r.get("body", ""),
                    }
                )
    except Exception as e:
        out.append({"title": "search error", "url": "", "snippet": str(e)})
    return out


TOOL_WEB_SEARCH = {
    "type": "function",
    "name": "web_search",
    "description": (
        "Search the web for current or factual information "
        "(news, papers, prices, dates, anything after your "
        "knowledge cutoff or that you are unsure about)."
    ),
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}
TOOL_SAVE_CITATION = {
    "type": "function",
    "name": "save_citation",
    "description": (
        "Save an academic reference to the user's citation "
        "manager. Use when the user asks to save/cite a paper, "
        "or when they clearly want to keep a reference found "
        "via search."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "authors": {"type": "string", "description": "e.g. Smith, J.; Doe, A."},
            "title": {"type": "string"},
            "year": {"type": "string"},
            "venue": {"type": "string", "description": "journal/conference"},
            "doi": {"type": "string"},
            "url": {"type": "string"},
        },
        "required": ["title"],
    },
}


# ------------------------------------------------------------------ memory (selective)
MEMORY_PROMPT = """You maintain long-term memory about a user of a research \
assistant. From the conversation below, extract NEW durable facts worth \
remembering long-term.

WORTH remembering: thesis/research topic and field, methodology, preferred \
citation style, programming languages/tools, preferred tone or writing \
style, name/role/institution, long-term goals.
NOT worth remembering: one-off requests, temporary questions, trivia they \
asked about, anything about the assistant's own answers.

Do NOT repeat facts already known.
Already known: {known}

Conversation:
{transcript}

Reply ONLY with JSON: {{"facts": ["fact 1", ...]}} — empty list if nothing \
is worth remembering (this is common and fine)."""


def responses_text(prompt, json_mode=False, kind=None, user_id=None):
    """`kind`/`user_id`: when both are given, logs token usage to
    ai_usage_ledger. Optional — most of this function's call sites don't
    pass them yet (chat, memory extraction, titles, compare, gap-finder,
    writing assistant); only extract_metadata and paper_analysis do
    today. Not logging is the safe default, not an error."""
    kwargs = dict(model=UTILITY_MODEL, input=prompt, store=False)
    if json_mode:
        kwargs["text"] = {"format": {"type": "json_object"}}
    resp = client.responses.create(**kwargs)
    usage = getattr(resp, "usage", None)
    record_ai_call(
        UTILITY_MODEL,
        prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
        completion_tokens=getattr(usage, "output_tokens", 0) or 0,
    )
    if kind and user_id:
        _log_ai_usage(
            user_id,
            kind,
            "utility_model",
            getattr(usage, "input_tokens", 0) or 0,
            getattr(usage, "output_tokens", 0) or 0,
        )
    return resp.output_text


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 3: automatic paper metadata extraction
# ══════════════════════════════════════════════════════════════════════════

import hashlib as _hashlib
import re as _re_meta

# The prompt is deliberately strict: return ONLY the JSON object, with null
# for any field that cannot be found in the text.  We do NOT ask it to
# invent, guess, or web-search — only extract from what is present.
_META_PROMPT = """You are a metadata extractor for academic papers.

Given the first portion of a research document, extract the following fields
exactly as they appear.  Return ONLY a JSON object — no markdown, no prose.
Use null for any field you cannot find with high confidence.

Fields:
  title       – full paper title (string | null)
  authors     – semicolon-separated author names, "Last, F." style (string | null)
  year        – 4-digit publication year (string | null)
  venue       – journal, conference, or publisher name (string | null)
  doi         – DOI string without "https://doi.org/" prefix (string | null)
  abstract    – full abstract text verbatim (string | null)
  keywords    – comma-separated keywords if listed (string | null)

Document excerpt (first 3 000 chars):
{excerpt}
"""


def _sha256(text: str) -> str:
    return _hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _extract_meta_from_text(text: str, user_id=None) -> dict:
    """Call the utility model to extract bibliographic metadata from `text`.

    Returns a dict with keys: title, authors, year, venue, doi, abstract,
    keywords — all strings or None.  Never raises: on any failure returns an
    empty dict so the caller can degrade gracefully."""
    excerpt = text[:3000]
    try:
        raw = responses_text(
            _META_PROMPT.format(excerpt=excerpt),
            json_mode=True,
            kind="metadata",
            user_id=user_id,
        )
        data = json.loads(raw)
    except Exception:
        return {}

    clean = {}
    for key in ("title", "authors", "year", "venue", "doi", "abstract", "keywords"):
        val = data.get(key)
        clean[key] = (
            str(val).strip()
            if val and str(val).strip() not in ("null", "None", "")
            else None
        )
    return clean


def _apply_metadata(file_id: int, text: str, content_hash: str, job_id=None) -> None:
    """Background task: extract metadata and write it to the UserFile row.

    Runs in a daemon thread so the upload HTTP response is already sent by
    the time this does its model call.  It is idempotent: if the content_hash
    already matches the stored one we skip the model call entirely.

    `job_id`: pass an already-claimed UploadJob id (the queue worker does)
    to skip creating/finishing a second, duplicate tracking row — the
    worker owns that row's lifecycle instead. Left None (default) for the
    legacy thread-spawned callers, which still manage their own row here."""
    db = SessionLocal()
    owns_job = job_id is None
    try:
        uf = db.get(UserFile, file_id)
        if not uf:
            return

        # Idempotency: if a previous run already processed this exact content,
        # do nothing.  Covers the case where the same paper is re-uploaded.
        if uf.content_hash == content_hash and uf.meta_status == "done":
            return

        if owns_job:
            job_id = _start_upload_job(db, uf.user_id, file_id, "extract_metadata")
        uf.meta_status = "running"
        db.commit()

        meta = _extract_meta_from_text(text, user_id=uf.user_id)

        # Re-fetch in case another thread touched the row while we were waiting
        uf = db.get(UserFile, file_id)
        if not uf:
            return

        uf.content_hash = content_hash
        uf.meta_status = "done"
        if meta.get("title"):
            uf.title = meta["title"][:500]
        if meta.get("authors"):
            uf.authors = meta["authors"][:1000]
        if meta.get("year"):
            # Validate: keep only if it looks like a 4-digit year
            y = _re_meta.search(r"(19|20)\d{2}", meta["year"] or "")
            if y:
                uf.year = y.group(0)
        if meta.get("venue"):
            uf.venue = meta["venue"][:300]
        if meta.get("doi"):
            uf.doi = meta["doi"][:200]
        if meta.get("abstract"):
            uf.abstract = meta["abstract"][:8000]
        db.commit()
        if owns_job:
            _finish_upload_job(db, job_id, ok=True)

    except Exception as exc:
        try:
            uf2 = db.get(UserFile, file_id)
            if uf2:
                uf2.meta_status = "failed"
                db.commit()
            if owns_job:
                _finish_upload_job(db, job_id, ok=False, error=exc)
        except Exception:
            pass
        if not owns_job:
            raise  # let the queue worker's own try/except apply retry/backoff
        logging.getLogger(__name__).warning(
            "metadata extraction failed for file %s: %s", file_id, exc
        )
    finally:
        db.close()


def extract_metadata(file_id: int, text: str, content_hash: str) -> None:
    """Fire-and-forget wrapper: starts _apply_metadata in a daemon thread."""
    threading.Thread(
        target=_apply_metadata,
        args=(file_id, text, content_hash),
        daemon=True,
    ).start()


def extract_metadata_sync(file_id: int, text: str, content_hash: str) -> None:
    """Synchronous variant for use in tests where threading complicates things."""
    _apply_metadata(file_id, text, content_hash)


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 4: Automatic Paper Analysis (14 fields)
# ══════════════════════════════════════════════════════════════════════════

# Every section is a concise, specific label — the model fills in the value.
# "null" is the correct answer when a section genuinely doesn't exist in the
# paper (e.g. a theory paper has no Dataset section).
ANALYSIS_FIELDS = [
    "executive_summary",  # 3–5 sentence plain-English overview
    "abstract_explained",  # abstract rewritten for a smart non-specialist
    "research_objective",  # what the paper is trying to achieve
    "problem_statement",  # the gap or problem it addresses
    "methodology",  # how the study was conducted
    "dataset",  # data used; null if not applicable
    "experiments",  # key experiments or evaluations run
    "results",  # main quantitative/qualitative findings
    "key_contributions",  # list of specific, novel contributions
    "strengths",  # what the paper does well
    "limitations",  # weaknesses, threats to validity, open questions
    "future_work",  # directions the authors or community should pursue
    "keywords",  # 5–10 technical keywords
    "important_terms",  # glossary: {term: one-line definition}
]

_ANALYSIS_PROMPT = """You are an expert research analyst. Analyse the paper below and return ONLY a JSON object — no markdown fences, no prose outside the object.

Each key maps to the content described. Use null when a section genuinely does not apply (e.g. no dataset for a pure theory paper). Never fabricate details not present in the text.

Keys and what to put in them:
  executive_summary   – 3–5 sentences: what is this paper, why does it matter
  abstract_explained  – rewrite the abstract for a smart non-specialist
  research_objective  – one sentence: what the paper is trying to achieve
  problem_statement   – the specific gap or problem being addressed
  methodology         – how the study was conducted (approach, framework, steps)
  dataset             – datasets used, sizes, sources (null if not applicable)
  experiments         – key experiments or evaluations described
  results             – main findings; include numbers if stated
  key_contributions   – JSON array of strings, each a distinct novel contribution
  strengths           – what the paper does particularly well (array of strings)
  limitations         – weaknesses, assumptions, threats to validity (array)
  future_work         – next steps suggested by authors or implied by gaps (array)
  keywords            – 5–10 technical keywords as a JSON array
  important_terms     – JSON object {{term: one-line definition}} for key jargon

Paper text (first {max_chars} characters):
{text}
"""

_ANALYSIS_MAX_CHARS = 12_000  # covers most papers; keeps prompt cost bounded


def _run_paper_analysis(
    file_id: int, text: str, content_hash: str, job_id=None
) -> None:
    """Background worker: generate and persist the 14-field paper analysis.

    Idempotent on content_hash: if the stored hash matches and status=='done'
    we skip the model call. 'force' refreshes bypass this check (see route).

    `job_id`: pass an already-claimed UploadJob id (the queue worker does)
    to skip creating/finishing a second, duplicate tracking row. Left
    None (default) for the legacy thread-spawned callers.
    """
    db = SessionLocal()
    owns_job = job_id is None
    try:
        pa = db.execute(
            select(PaperAnalysis).where(PaperAnalysis.file_id == file_id)
        ).scalar_one_or_none()

        if pa is None:
            pa = PaperAnalysis(
                file_id=file_id, user_id=db.get(UserFile, file_id).user_id
            )
            db.add(pa)
            db.commit()

        # Idempotency check
        if pa.content_hash == content_hash and pa.status == "done":
            return

        if owns_job:
            job_id = _start_upload_job(db, pa.user_id, file_id, "paper_analysis")
        pa.status = "running"
        pa.error = ""
        db.commit()

        prompt = _ANALYSIS_PROMPT.format(
            max_chars=_ANALYSIS_MAX_CHARS,
            text=text[:_ANALYSIS_MAX_CHARS],
        )
        raw = responses_text(
            prompt, json_mode=True, kind="analysis", user_id=pa.user_id
        )
        data = json.loads(raw)

        # Normalise: ensure array fields are lists, terms dict is a dict
        for arr_field in (
            "key_contributions",
            "strengths",
            "limitations",
            "future_work",
            "keywords",
        ):
            v = data.get(arr_field)
            if isinstance(v, str):
                data[arr_field] = [v] if v else []
            elif not isinstance(v, list):
                data[arr_field] = []

        if not isinstance(data.get("important_terms"), dict):
            data["important_terms"] = {}

        # Re-fetch in case a concurrent request modified the row
        pa = db.execute(
            select(PaperAnalysis).where(PaperAnalysis.file_id == file_id)
        ).scalar_one_or_none()
        if pa is None:
            return

        pa.status = "done"
        pa.content_hash = content_hash
        pa.model = UTILITY_MODEL
        pa.data = json.dumps(data, ensure_ascii=False)
        pa.error = ""
        db.commit()
        if owns_job:
            _finish_upload_job(db, job_id, ok=True)

    except Exception as exc:
        try:
            pa2 = db.execute(
                select(PaperAnalysis).where(PaperAnalysis.file_id == file_id)
            ).scalar_one_or_none()
            if pa2:
                pa2.status = "failed"
                pa2.error = str(exc)[:500]
                db.commit()
            if owns_job:
                _finish_upload_job(db, job_id, ok=False, error=exc)
        except Exception:
            pass
        if not owns_job:
            raise  # let the queue worker's own try/except apply retry/backoff
        logging.getLogger(__name__).warning(
            "paper analysis failed for file %s: %s", file_id, exc
        )
    finally:
        db.close()


def trigger_paper_analysis(
    file_id: int, text: str, content_hash: str, sync: bool = False
) -> None:
    """Fire paper analysis in a background thread (or inline when sync=True)."""
    if sync:
        _run_paper_analysis(file_id, text, content_hash)
    else:
        threading.Thread(
            target=_run_paper_analysis,
            args=(file_id, text, content_hash),
            daemon=True,
        ).start()


def _analysis_to_dict(pa: PaperAnalysis) -> dict:
    """Serialise a PaperAnalysis row to the public API shape."""
    data = {}
    if pa.data:
        try:
            data = json.loads(pa.data)
        except Exception:
            pass
    return {
        "file_id": pa.file_id,
        "status": pa.status,
        "error": pa.error or "",
        "model": pa.model or "",
        "updated_at": pa.updated_at.isoformat() if pa.updated_at else None,
        "data": data,
    }


def _file_to_dict(x: UserFile) -> dict:
    """Serialise a UserFile to the JSON shape the frontend expects.

    Centralising this means every route (upload, list, patch, …) returns
    exactly the same shape and there is one place to add fields."""
    return {
        "id": x.id,
        "name": x.name,
        "kind": x.kind,
        "size": x.size,
        "project_id": x.project_id,
        "conversation_id": x.conversation_id,
        "chunks": len(x.chunks),
        # ── research metadata ──
        "title": x.title or "",
        "authors": x.authors or "",
        "year": x.year or "",
        "venue": x.venue or "",
        "doi": x.doi or "",
        "abstract": x.abstract or "",
        "reading_status": x.reading_status or "unread",
        "tags": json.loads(x.tags) if x.tags else [],
        "meta_status": x.meta_status or "pending",
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }


def extract_memories(user_id, project_id, convo_messages):
    db = SessionLocal()
    try:
        existing = [
            m.fact
            for m in db.execute(
                select(Memory).where(Memory.user_id == user_id)
            ).scalars()
        ]
        transcript = "\n".join(
            f"{m['role']}: {str(m['content'])[:500]}" for m in convo_messages[-10:]
        )
        text = responses_text(
            MEMORY_PROMPT.format(known=json.dumps(existing), transcript=transcript),
            json_mode=True,
        )
        facts = json.loads(text).get("facts", [])
        for f in facts[:5]:
            if f and f not in existing:
                db.add(Memory(user_id=user_id, project_id=project_id, fact=f[:1000]))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def generate_title(first_user_msg, first_reply):
    try:
        t = responses_text(
            "Write a short title (2-5 words, no quotes, no punctuation at the "
            "end) for a chat that starts like this:\n"
            f"user: {str(first_user_msg)[:400]}\nassistant: {first_reply[:400]}"
        )
        return (t or "").strip().strip('"')[:60] or None
    except Exception:
        return None


def build_paper_chat_prompt(user, paper):
    """Focused system prompt for Paper Chat (M7).

    The AI is restricted to the single uploaded paper — it must not fabricate,
    must cite by page/section, and must say so when the answer is not present.
    """
    paper_title = paper.title or paper.name
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
        f"User: {user.name}",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ]
    if paper.authors:
        meta.append(f"Authors: {paper.authors}")
    if paper.year:
        meta.append(f"Year: {paper.year}")
    if paper.venue:
        meta.append(f"Venue: {paper.venue}")
    return header + "\n\n" + body + "\n\n" + "\n".join(meta)


# Static opening sentence only — everything else build_system_prompt()
# assembles below (user name, date, custom instructions, project,
# memories) is computed per-request and was never a good fit for a
# template row. backfill.py already seeds this exact text under the name
# "chat_system"; PromptRegistry is tried first, with this literal string
# as the fallback for a fresh DB backfill.py hasn't run against yet (or
# a deleted/corrupted row) — a chat request must never fail just because
# a prompt lookup did.
_CHAT_SYSTEM_FALLBACK = (
    "You are Personal AI, a helpful assistant specialised in academic "
    "research and thesis writing, but able to help with anything. "
    "Use markdown. Be precise with citations and honest about "
    "uncertainty. When you used web search results or document excerpts, "
    "cite the sources inline."
)


def _get_chat_system_opening(db):
    try:
        return get_prompt_registry(db).get_prompt("chat_system")
    except (ValueError, TemplateError):
        return _CHAT_SYSTEM_FALLBACK
    except Exception:
        logging.getLogger(__name__).warning(
            "chat_system prompt fetch failed, using fallback", exc_info=True
        )
        return _CHAT_SYSTEM_FALLBACK


def _log_chat_cost(user_id, model, usage):
    """Best-effort — a logging failure must never break an otherwise-
    successful chat response, same reasoning as every other best-effort
    cost-logging call site in this app. /api/chat calls
    client.responses.create() directly (never went through
    responses_text()), so unlike extract_metadata/paper_analysis this
    route had NO cost logging at all until now — a real gap being
    closed, not a duplicate of anything."""
    if not usage:
        return
    prompt_tokens = getattr(usage, "input_tokens", 0) or 0
    completion_tokens = getattr(usage, "output_tokens", 0) or 0
    record_ai_call(model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    try:
        ledger = get_cost_ledger()
        cost = ledger.estimate_cost(model, prompt_tokens, completion_tokens)
        db = SessionLocal()
        try:
            ledger.log(
                db, user_id=user_id, model=model, prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=cost, action="chat",
            )
        finally:
            db.close()
    except Exception:
        logging.getLogger(__name__).warning("chat cost logging failed", exc_info=True)


def build_system_prompt(user, project, memory_enabled=True):
    global_mems, proj_mems = [], []
    db = SessionLocal()
    try:
        if memory_enabled:
            global_mems = [
                m.fact
                for m in db.execute(
                    select(Memory).where(
                        Memory.user_id == user.id, Memory.project_id.is_(None)
                    )
                ).scalars()
            ]
            if project:
                proj_mems = [
                    m.fact
                    for m in db.execute(
                        select(Memory).where(
                            Memory.user_id == user.id, Memory.project_id == project.id
                        )
                    ).scalars()
                ]
        opening = _get_chat_system_opening(db)
    finally:
        db.close()

    parts = [
        opening,
        f"The user's name is {user.name}.",
        f"Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M')}.",
    ]
    if user.custom_instructions:
        parts.append(
            "The user's custom instructions (always follow):\n"
            + user.custom_instructions
        )
    if project:
        parts.append(f'Current project: "{project.name}".')
        if project.instructions:
            parts.append("Project instructions from the user:\n" + project.instructions)
    if global_mems:
        parts.append(
            "Things you remember about the user:\n"
            + "\n".join(f"- {m}" for m in global_mems)
        )
    if proj_mems:
        parts.append(
            "Things you remember in this project:\n"
            + "\n".join(f"- {m}" for m in proj_mems)
        )
    return "\n\n".join(parts)


# ------------------------------------------------------------------ API: profile / models
@app.route("/api/me")
@login_required
def api_me():
    db = SessionLocal()
    try:
        user = db.get(User, session["user_id"])
        return jsonify(
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "picture": user.picture or "",
                "custom_instructions": user.custom_instructions or "",
                "default_model": DEFAULT_MODEL,
            }
        )
    finally:
        db.close()


@app.route("/api/profile", methods=["PATCH"])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        u = db.get(User, session["user_id"])
        if "custom_instructions" in data:
            u.custom_instructions = str(data["custom_instructions"])[:4000]
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/models")
@login_required
def api_models():
    force = request.args.get("refresh") == "1"
    return jsonify({"models": get_models(force=force), "default": DEFAULT_MODEL})


# ------------------------------------------------------------------ API: files
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")  # vision-API formats
MAX_UPLOAD_BYTES = MAX_FILE_MB * 1024 * 1024

# ---- storage architecture: presigned/multipart upload config -------------
MULTIPART_THRESHOLD_BYTES = (
    int(os.environ.get("MULTIPART_THRESHOLD_MB", "25")) * 1024 * 1024
)
UPLOAD_PART_BYTES = int(os.environ.get("UPLOAD_PART_SIZE_MB", "8")) * 1024 * 1024
UPLOAD_SESSION_TTL_SECONDS = (
    int(os.environ.get("UPLOAD_SESSION_TTL_MINUTES", "60")) * 60
)


def _find_duplicate_file(db, user_id, checksum):
    """Storage-level dedup, scoped per-user (not global) — a global
    content-addressed store would need reference counting before a delete
    could ever remove the underlying object, which isn't worth it for a
    personal-scale library and would blur the per-user isolation this app
    otherwise guarantees."""
    if not checksum:
        return None
    existing = (
        db.execute(
            select(UserFile).where(
                UserFile.user_id == user_id, UserFile.checksum_sha256 == checksum
            )
        )
        .scalars()
        .first()
    )
    if not existing:
        return None
    # A DB row whose object has since gone missing from storage (deleted
    # out-of-band, reconciliation hasn't caught it yet) must not be handed
    # back as if the bytes still exist.
    if storage.storage_manager.provider.head(existing.path) is None:
        return None
    return existing


def _start_upload_job(db, user_id, file_id, job_type):
    """Create an UploadJob row and return its id. This tracks today's
    still-synchronous/threading-based processing — it is the foundation a
    future queue (processing-pipeline-architecture.md) reads from, not a
    queue itself; execution here is unchanged, only observed."""
    job = UploadJob(
        user_id=user_id,
        file_id=file_id,
        job_type=job_type,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    return job.id


def _finish_upload_job(db, job_id, ok, error=None):
    job = db.get(UploadJob, job_id)
    if not job:
        return
    job.status = "done" if ok else "failed"
    job.finished_at = datetime.now(timezone.utc)
    if error is not None:
        job.attempts = (job.attempts or 0) + 1
        job.last_error = str(error)[:2000]
    db.commit()


def _enqueue_job(db, user_id, file_id, job_type, upload_batch_id=None):
    """Create an UploadJob + its paired OutboxEvent in one transaction —
    the same transactional-outbox pattern upload_file() uses, factored out
    so the queue worker can chain follow-on stages (import -> extract_
    metadata -> paper_analysis) the same way instead of spawning threads.
    Does not commit: caller folds this into its own transaction."""
    job = UploadJob(
        upload_batch_id=upload_batch_id,
        file_id=file_id,
        user_id=user_id,
        job_type=job_type,
        status="pending",
    )
    db.add(job)
    db.flush()  # assigns job.id
    db.add(
        OutboxEvent(
            aggregate_type="upload_job",
            aggregate_id=job.id,
            event_type="job.enqueued",
            payload=json.dumps({"file_id": file_id}),
        )
    )
    return job.id


_redis_client = None


def _get_redis():
    """Lazy singleton; returns None if Redis isn't configured or isn't
    reachable. Every caller must treat None as "cache unavailable, fall
    back to Postgres" — deliberately not memoized as permanently
    unavailable, so a Redis instance that comes up later is picked up on
    the very next call instead of staying disabled for the process
    lifetime."""
    global _redis_client
    if not REDIS_URL:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_lib

        client = redis_lib.from_url(
            REDIS_URL, socket_connect_timeout=2, socket_timeout=2, decode_responses=True
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        logging.getLogger(__name__).warning(
            "Redis unavailable — job-status cache disabled"
        )
        return None


def _set_job_status_cache(job_id, status, progress, updated_at, user_id):
    """user_id is cached alongside status/progress/updated_at — not part
    of the spec'd hash shape, but a cache-hit response still has to pass
    the same ownership check every other route in this app does, and that
    needs user_id available without a Postgres round-trip (defeating the
    point of the cache) to check it against."""
    r = _get_redis()
    if not r:
        return
    key = f"job:{job_id}:status"
    try:
        r.hset(
            key,
            mapping={
                "status": status,
                "progress": progress,
                "updated_at": updated_at.isoformat() if updated_at else "",
                "user_id": user_id,
            },
        )
        r.expire(key, JOB_STATUS_CACHE_TTL_SECONDS)
    except Exception:
        logging.getLogger(__name__).warning(
            "job-status cache write failed", exc_info=True
        )


def _get_job_status_cache(job_id):
    r = _get_redis()
    if not r:
        return None
    try:
        data = r.hgetall(f"job:{job_id}:status")
        return data or None
    except Exception:
        logging.getLogger(__name__).warning(
            "job-status cache read failed", exc_info=True
        )
        return None


# Small static per-model price table (USD per 1K tokens) — update by hand
# when OpenAI changes pricing, same approach devops-observability.md §3
# recommends over integrating a billing API for this scale of app.
#
# gpt-5-mini was previously listed here with a specific rate while
# backend/ai/cost_ledger.py's CostLedger.PRICING deliberately excluded the
# whole gpt-5 family as unverified (its own docstring: "a wrong-but-
# confident-looking dollar figure is worse than an honest unknown") — two
# tables disagreeing about whether the same number was trustworthy.
# Reconciled toward the more conservative policy: removed here too, so an
# unpriced model returns cost=0.0 everywhere in this app, consistently,
# rather than a real number in one place and a deliberate "we don't know"
# in the other. Re-add with a real rate once OpenAI's published gpt-5-mini
# pricing is actually confirmed against their pricing page.
_PRICE_PER_1K_TOKENS = {
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "text-embedding-3-small": {"prompt": 0.00002, "completion": 0.0},
}


def _get_active_model_version_id(logical_name):
    """Look up the seeded/active model_versions row for a logical name
    (backfill.py's Task 3 pass seeds default_model/utility_model/
    embed_model, version 1, active). Returns None if none is seeded —
    callers must treat that as "don't log this usage", not fail the
    actual AI call over missing cost-tracking metadata."""
    db = SessionLocal()
    try:
        row = (
            db.execute(
                select(ModelVersion).where(
                    ModelVersion.logical_name == logical_name,
                    ModelVersion.is_active == True,
                )  # noqa: E712 (SQLAlchemy needs == True, not `is True`, for a Column comparison)
            )
            .scalars()
            .first()
        )
        return row.id if row else None
    finally:
        db.close()


def _log_ai_usage(user_id, kind, logical_model_name, prompt_tokens, completion_tokens):
    """Best-effort: never let a cost-tracking failure break the AI call it's
    tracking. Silently does nothing if no active model_versions row is
    seeded (e.g. backfill.py hasn't been run) or the write itself fails."""
    if not user_id:
        return
    try:
        model_version_id = _get_active_model_version_id(logical_model_name)
        if not model_version_id:
            return
        cost = 0.0
        db = SessionLocal()
        try:
            mv = db.get(ModelVersion, model_version_id)
            prices = _PRICE_PER_1K_TOKENS.get(mv.provider_model_id) if mv else None
            if prices:
                cost = (prompt_tokens / 1000) * prices["prompt"] + (
                    completion_tokens / 1000
                ) * prices["completion"]
            db.add(
                AIUsageLedger(
                    user_id=user_id,
                    kind=kind,
                    model_version_id=model_version_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        logging.getLogger(__name__).warning("ai usage logging failed", exc_info=True)


def _adjust_storage_usage(db, user_id, delta_bytes, delta_files):
    """Live per-user storage total, updated in the same transaction as the
    upload/delete that changes it — get-or-create, then increment. Does
    NOT commit: callers fold this into their own transaction boundary
    (some need it atomic with several other writes), and must commit
    themselves."""
    usage = db.get(StorageUsage, user_id)
    if not usage:
        usage = StorageUsage(user_id=user_id, bytes_used=0, file_count=0)
        db.add(usage)
    usage.bytes_used = max(0, (usage.bytes_used or 0) + delta_bytes)
    usage.file_count = max(0, (usage.file_count or 0) + delta_files)


def _process_document(db, uf, path, name, mime, job_id=None, on_processed=None):
    """Extract, chunk, embed, and persist Chunk rows for a document that's
    already stored. Shared by the direct-upload route, the presigned-upload
    confirm route, and the queue worker, so all three go through identical
    processing. Returns the user-facing `note` (None on a normal successful
    index).

    `job_id`: pass an already-claimed UploadJob id (the queue worker does)
    to skip creating/finishing a second, duplicate tracking row — the
    worker owns that row's lifecycle instead.

    `on_processed(file_id, text, content_hash)`: called once real text has
    been extracted and chunked, instead of the default behaviour (spawning
    the legacy extract_metadata()/trigger_paper_analysis() daemon threads).
    The queue worker passes one that enqueues the next jobs transactionally
    instead of spawning threads."""
    owns_job = job_id is None
    if owns_job:
        job_id = _start_upload_job(db, uf.user_id, uf.id, "import")
    try:
        lower = name.lower()
        text = extract_text(path, mime, name)
        is_note = (
            bool(text)
            and text.startswith("[")
            and text.endswith("]")
            and len(text) < 400
        )
        note = None
        n_chunks = 0

        if not text:
            # No readable text — e.g. a scanned/image PDF or a binary blob.
            uf.text_len = 0
            note = (
                "scanned_pdf"
                if (lower.endswith(".pdf") or "pdf" in (mime or ""))
                else "no_text"
            )
        elif is_note:
            uf.text_len = 0
            note = text.strip("[]")
        else:
            uf.text_len = len(text)
            # Use the locator-aware chunker for PDFs and DOCX so every chunk
            # knows its page / section; fall back to plain chunking for
            # everything else (pptx, xlsx, txt …).
            is_locatable = (
                lower.endswith(".pdf")
                or "pdf" in (mime or "")
                or lower.endswith(".docx")
            )
            if is_locatable:
                doc_chunks = chunk_document(text)
                pieces = [c["content"] for c in doc_chunks]
                embs = embed_texts(pieces, user_id=uf.user_id) if pieces else []
                for i, (ch_dict, e) in enumerate(zip(doc_chunks, embs)):
                    db.add(
                        Chunk(
                            file_id=uf.id,
                            idx=i,
                            content=ch_dict["content"],
                            embedding=json.dumps(e) if e else None,
                            page=ch_dict.get("page"),
                            section=ch_dict.get("section"),
                        )
                    )
            else:
                pieces = chunk_text(text)
                embs = embed_texts(pieces, user_id=uf.user_id) if pieces else []
                for i, (p, e) in enumerate(zip(pieces, embs)):
                    db.add(
                        Chunk(
                            file_id=uf.id,
                            idx=i,
                            content=p,
                            embedding=json.dumps(e) if e else None,
                        )
                    )
            n_chunks = len(pieces)
        db.commit()

        # Fire metadata + paper analysis asynchronously so the HTTP response is
        # not blocked by model calls. Only for documents with real extracted text.
        if text and not is_note and n_chunks > 0:
            h = _sha256(text)
            # Persist hash immediately so both background jobs can use it for
            # their idempotency checks.
            db2 = SessionLocal()
            try:
                uf2 = db2.get(UserFile, uf.id)
                if uf2:
                    uf2.content_hash = h
                    db2.commit()
            finally:
                db2.close()
            if on_processed:
                on_processed(uf.id, text, h)
            else:
                extract_metadata(uf.id, text, h)  # M3: bibliographic fields
                trigger_paper_analysis(uf.id, text, h)  # M4: 14-field analysis

        if owns_job:
            _finish_upload_job(db, job_id, ok=True)
        return note
    except Exception as exc:
        if owns_job:
            _finish_upload_job(db, job_id, ok=False, error=exc)
        else:
            raise  # let the queue worker's own try/except apply retry/backoff


@app.route("/api/files", methods=["POST"])
@login_required
def upload_file():
    """Validate, store, and enqueue — nothing else. Extraction/chunking/
    embedding no longer happen here (compare to confirm_upload(), which
    still processes inline for now): this route's only job is to commit
    an UploadJob + its OutboxEvent in the same transaction as the file
    row, so a Queue Worker polling upload_jobs/outbox_events can pick the
    work up. Replaces the old threading.Thread(daemon=True) call — that
    approach had a real gap this closes: if the process died between
    committing the file row and starting the thread, the work was silently
    lost forever. Here, either the whole transaction commits (job + event
    together) or none of it does — there is no window where a job exists
    without the event that will get it picked up."""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "no_file"}), 400
    name = f.filename
    lower = name.lower()
    # Accept ANY file type. Images go to the vision path; everything else is
    # treated as a document and run through the text extractor.
    kind = "image" if lower.endswith(IMAGE_EXT) else "document"

    conversation_id = request.form.get("conversation_id", type=int)
    project_id = request.form.get("project_id", type=int)
    batch_id = request.form.get("batch_id", type=int)  # not sent by any UI yet
    ext = os.path.splitext(lower)[1]
    disk_name = uuid.uuid4().hex + ext
    # Saved locally only long enough to size-check, hash, and upload —
    # extraction no longer happens in this request. Removed in the
    # `finally` below either way.
    path = os.path.join(UPLOAD_DIR, disk_name)
    f.save(path)
    size = os.path.getsize(path)
    if size > MAX_UPLOAD_BYTES:
        try:
            os.remove(path)
        except OSError:
            pass
        return (
            jsonify(
                {"error": "too_large", "detail": f"Max file size is {MAX_FILE_MB} MB"}
            ),
            400,
        )

    checksum = storage.sha256_file(path)
    uid = session["user_id"]

    db = SessionLocal()
    try:
        # Duplicate detection: this exact content already lives in the
        # user's library — skip the storage upload and the queue entirely
        # and hand back the existing file instead of paying for either.
        dup = _find_duplicate_file(db, uid, checksum)
        if dup:
            result = _file_to_dict(dup)
            result["note"] = None
            result["duplicate"] = True
            return jsonify(result)

        try:
            storage.upload(disk_name, path)
        except Exception:
            logging.exception("storage upload failed for %s", disk_name)
            return jsonify({"error": "storage_unavailable"}), 502

        # ---- everything below is one transaction: batch, quota check,
        # file row, job, outbox event, and the usage counter all commit
        # together or none of them do. ----

        # One batch per request today — no bulk-upload UI passes batch_id
        # yet (upload-ux.md's Bulk Upload page is what will start sending
        # one), so this just groups a single file under its own batch.
        batch = db.get(UploadBatch, batch_id) if batch_id else None
        if not batch or batch.user_id != uid:
            batch = UploadBatch(
                user_id=uid,
                project_id=project_id,
                conversation_id=conversation_id,
                source="library",
                file_count=0,
            )
            db.add(batch)
            db.flush()  # assigns batch.id without committing yet
        batch.file_count = (batch.file_count or 0) + 1

        usage = db.get(StorageUsage, uid)
        already_used = usage.bytes_used if usage else 0
        # Same limit QuotaService.check_storage_quota() uses for
        # /api/documents/upload (per-user override, DEFAULT_STORAGE_LIMIT_BYTES
        # otherwise) — this used to compare against the standalone
        # MAX_STORAGE_MB env var instead, which defaults to 5000 MB vs
        # QuotaService's ~1000 MB default: two routes silently enforcing
        # different limits, not really "the same limit, two code paths" as
        # once believed. Checked inline against the same `db` session/
        # transaction rather than via quota_service.check_storage_quota()
        # itself — that call opens its own session, which would lose the
        # atomicity _adjust_storage_usage()'s docstring depends on (this
        # check rolling back the batch/file inserts together on failure).
        user_row = db.get(User, uid)
        limit_bytes = (
            (user_row.storage_limit_bytes if user_row else None)
            or quota_service.DEFAULT_STORAGE_LIMIT_BYTES
        )
        if already_used + size > limit_bytes:
            db.rollback()  # undoes the batch insert/increment above too
            try:
                os.remove(path)
            except OSError:
                pass
            return (
                jsonify(
                    {
                        "error": "storage_quota_exceeded",
                        "detail": f"Storage limit is {limit_bytes // (1024 * 1024)} MB",
                    }
                ),
                403,
            )

        uf = UserFile(
            user_id=uid,
            project_id=project_id,
            conversation_id=conversation_id,
            name=name[:300],
            mime=f.mimetype,
            kind=kind,
            path=disk_name,
            size=size,
            checksum_sha256=checksum,
        )
        db.add(uf)
        db.flush()  # assigns uf.id

        # Images never went through the import pipeline (no extraction/
        # chunking/embedding applies — they're sent as vision input at
        # chat time instead), same as the old `if kind == "document":
        # _process_document(...)` guard. No job, no event, for an image.
        job_id = None
        if kind == "document":
            job = UploadJob(
                upload_batch_id=batch.id,
                file_id=uf.id,
                user_id=uid,
                job_type="import",
                status="pending",
            )
            db.add(job)
            db.flush()  # assigns job.id
            job_id = job.id

            db.add(
                OutboxEvent(
                    aggregate_type="upload_job",
                    aggregate_id=job.id,
                    event_type="job.enqueued",
                    payload=json.dumps({"file_id": uf.id}),
                )
            )

        _adjust_storage_usage(db, uid, delta_bytes=size, delta_files=1)

        db.commit()

        result = _file_to_dict(uf)
        result["note"] = None
        result["job_id"] = job_id
        return jsonify(result)
    finally:
        db.close()
        try:
            os.remove(path)
        except OSError:
            pass


@app.route("/api/jobs/<int:job_id>/status")
@login_required
def job_status(job_id):
    """Frontend status polling. Checks Redis first; on a cache miss, reads
    upload_jobs (the source of truth) and populates the cache for next
    time. A cache hit still needs the ownership check every route in this
    app does — see _set_job_status_cache's note on why user_id rides
    along in the cached hash instead of triggering a Postgres lookup just
    for that."""
    cached = _get_job_status_cache(job_id)
    if cached:
        if int(cached.get("user_id", 0)) != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        return jsonify(
            {
                "job_id": job_id,
                "status": cached.get("status"),
                "progress": int(cached.get("progress") or 0),
                "updated_at": cached.get("updated_at") or None,
                "cached": True,
            }
        )

    db = SessionLocal()
    try:
        job = db.get(UploadJob, job_id)
        if not job or job.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        # No granular checkpoint/percentage exists yet (that's the Step
        # Runner's job — processing-pipeline-architecture.md §5, not built)
        # — 100 once done, 0 otherwise is what's honestly available today.
        progress = 100 if job.status == "done" else 0
        _set_job_status_cache(job_id, job.status, progress, job.updated_at, job.user_id)
        return jsonify(
            {
                "job_id": job_id,
                "status": job.status,
                "progress": progress,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "cached": False,
            }
        )
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# Storage architecture — presigned / multipart uploads
#
# Bytes go straight from the browser to storage instead of proxying through
# this server twice (browser→Flask, then Flask→R2). Three calls:
#   1. POST /api/uploads/presign            → get a URL (or multipart part
#                                              URLs) to PUT bytes to
#   2. POST /api/uploads/multipart/complete → multipart only
#   3. POST /api/uploads/confirm            → server verifies the object
#                                              landed, then creates the
#                                              UserFile row and processes it
#
# Not yet wired into the frontend (Composer.tsx still uses the direct
# /api/files POST above) — this is the backend half of that migration.
# ══════════════════════════════════════════════════════════════════════════


@app.route("/api/uploads/presign", methods=["POST"])
@login_required
def presign_upload():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("filename") or "").strip()
    mime = data.get("mime") or "application/octet-stream"
    size = int(data.get("size") or 0)
    checksum = (data.get("checksum_sha256") or "").strip().lower() or None
    project_id = data.get("project_id")
    conversation_id = data.get("conversation_id")

    if not name or size <= 0:
        return jsonify({"error": "invalid_request"}), 400
    if size > MAX_UPLOAD_BYTES:
        return (
            jsonify(
                {"error": "too_large", "detail": f"Max file size is {MAX_FILE_MB} MB"}
            ),
            400,
        )

    db = SessionLocal()
    try:
        if checksum:
            dup = _find_duplicate_file(db, session["user_id"], checksum)
            if dup:
                # Client already has the bytes we'd need — nothing to
                # upload at all.
                return jsonify({"duplicate": True, "file": _file_to_dict(dup)})

        provider = storage.storage_manager.provider
        key = storage.storage_manager.new_key(os.path.splitext(name.lower())[1])
        use_multipart = provider.supports_multipart and size > MULTIPART_THRESHOLD_BYTES

        us = UploadSession(
            user_id=session["user_id"],
            project_id=project_id,
            conversation_id=conversation_id,
            key=key,
            name=name[:300],
            mime=mime,
            size_expected=size,
            checksum_sha256=checksum,
            status="pending",
        )
        db.add(us)
        db.commit()

        if use_multipart:
            upload_id = provider.create_multipart_upload(key, mime)
            us.upload_id = upload_id
            db.commit()
            part_count = math.ceil(size / UPLOAD_PART_BYTES)
            parts = [
                {
                    "part_number": i + 1,
                    "url": provider.presigned_part_url(key, upload_id, i + 1),
                }
                for i in range(part_count)
            ]
            return jsonify(
                {
                    "mode": "multipart",
                    "session_id": us.id,
                    "key": key,
                    "upload_id": upload_id,
                    "part_size": UPLOAD_PART_BYTES,
                    "parts": parts,
                }
            )

        put_url = provider.presigned_put_url(
            key, mime, expires_in=UPLOAD_SESSION_TTL_SECONDS
        )
        return jsonify(
            {"mode": "single", "session_id": us.id, "key": key, "put_url": put_url}
        )
    finally:
        db.close()


@app.route("/api/uploads/multipart/complete", methods=["POST"])
@login_required
def complete_multipart_upload_route():
    data = request.get_json(force=True, silent=True) or {}
    session_id = data.get("session_id")
    parts = data.get("parts") or []

    db = SessionLocal()
    try:
        us = db.get(UploadSession, session_id)
        if not us or us.user_id != session["user_id"] or not us.upload_id:
            return jsonify({"error": "not_found"}), 404

        provider = storage.storage_manager.provider
        try:
            provider.complete_multipart_upload(
                us.key,
                us.upload_id,
                [
                    storage.UploadPart(part_number=p["part_number"], etag=p["etag"])
                    for p in parts
                ],
            )
        except Exception:
            logging.exception("multipart complete failed for session %s", session_id)
            provider.abort_multipart_upload(us.key, us.upload_id)
            us.status = "aborted"
            db.commit()
            return jsonify({"error": "multipart_complete_failed"}), 502

        us.status = "uploaded"
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/uploads/confirm", methods=["POST"])
@login_required
def confirm_upload():
    data = request.get_json(force=True, silent=True) or {}
    session_id = data.get("session_id")
    content_md5_b64 = data.get("content_md5_b64")

    db = SessionLocal()
    try:
        us = db.get(UploadSession, session_id)
        if not us or us.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        if us.status == "confirmed":
            return jsonify({"error": "already_confirmed"}), 409

        provider = storage.storage_manager.provider
        info = provider.head(us.key)
        if info is None:
            return jsonify({"error": "object_not_found"}), 400
        if us.size_expected and info.size != us.size_expected:
            return jsonify({"error": "size_mismatch"}), 400

        # Whole-file checksum verification only applies to single-part
        # uploads — a multipart ETag is a hash of the part hashes, not an
        # MD5 of the object. Multipart corruption is instead caught
        # per-part, at upload time, by the Content-MD5 each PUT already
        # carried (R2/S3 reject a part outright if it doesn't match).
        if content_md5_b64 and not us.upload_id and info.etag:
            expected_hex = binascii.hexlify(base64.b64decode(content_md5_b64)).decode()
            if expected_hex != info.etag:
                provider.delete(us.key)
                us.status = "aborted"
                db.commit()
                return jsonify({"error": "checksum_mismatch"}), 400

        # Re-check dedup at confirm time too: two presigns for the same
        # content can race ahead of each other between presign and confirm.
        if us.checksum_sha256:
            dup = _find_duplicate_file(db, session["user_id"], us.checksum_sha256)
            if dup:
                provider.delete(us.key)
                us.status = "confirmed"
                db.commit()
                result = _file_to_dict(dup)
                result["note"] = None
                result["duplicate"] = True
                return jsonify(result)

        lower = us.name.lower()
        kind = "image" if lower.endswith(IMAGE_EXT) else "document"
        uf = UserFile(
            user_id=session["user_id"],
            project_id=us.project_id,
            conversation_id=us.conversation_id,
            name=us.name,
            mime=us.mime,
            kind=kind,
            path=us.key,
            size=info.size,
            checksum_sha256=us.checksum_sha256,
        )
        db.add(uf)
        us.status = "confirmed"
        _adjust_storage_usage(
            db, session["user_id"], delta_bytes=info.size, delta_files=1
        )
        db.commit()

        note = None
        if kind == "document":
            with provider.local_copy(
                us.key, suffix=os.path.splitext(lower)[1]
            ) as local_path:
                note = _process_document(db, uf, local_path, us.name, us.mime)

        db3 = SessionLocal()
        try:
            uf_out = db3.get(UserFile, uf.id)
            result = _file_to_dict(uf_out) if uf_out else {}
        finally:
            db3.close()
        result["note"] = note
        return jsonify(result)
    finally:
        db.close()


@app.route("/api/uploads/local-put/<key>", methods=["PUT"])
def local_upload_put(key):
    """Only meaningful when LocalProvider is active — gives local/dev
    deployments the same presigned-URL shape as R2 without a real object
    store to bypass. Auth is the signed token itself, not the session
    cookie, matching how a real presigned URL works (no login required to
    use it, just possession of the URL)."""
    provider = storage.storage_manager.provider
    if not hasattr(provider, "verify_token"):
        return jsonify({"error": "not_supported"}), 404
    try:
        payload = provider.verify_token(
            request.args.get("token", ""), max_age=UPLOAD_SESSION_TTL_SECONDS
        )
    except ValueError:
        return jsonify({"error": "invalid_token"}), 403
    if payload.get("key") != key:
        return jsonify({"error": "invalid_token"}), 403

    tmp_path = os.path.join(UPLOAD_DIR, "put_" + uuid.uuid4().hex)
    try:
        with open(tmp_path, "wb") as out:
            shutil.copyfileobj(request.stream, out)
        provider.upload(key, tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    return jsonify({"ok": True})


@app.route("/api/uploads/local-get/<key>")
def local_upload_get(key):
    provider = storage.storage_manager.provider
    if not hasattr(provider, "verify_token"):
        return jsonify({"error": "not_supported"}), 404
    try:
        payload = provider.verify_token(request.args.get("token", ""), max_age=300)
    except ValueError:
        return jsonify({"error": "invalid_token"}), 403
    if payload.get("key") != key:
        return jsonify({"error": "invalid_token"}), 403
    return send_file(
        provider.path_for(key),
        mimetype=payload.get("mime"),
        download_name=payload.get("name"),
        as_attachment=True,
    )


# ------------------------------------------------------------------ storage maintenance CLI
# Run with `flask --app server sweep-temp` / `gc-storage` / `reconcile-storage`.


@app.cli.command("sweep-temp")
def sweep_temp_cmd():
    """Delete stray files left in UPLOAD_DIR by a request that crashed
    before its own cleanup ran."""
    removed = storage.sweep_temp_dir(
        UPLOAD_DIR, max_age_seconds=UPLOAD_SESSION_TTL_SECONDS
    )
    click.echo(f"sweep-temp: removed {len(removed)} stale temp file(s)")


@app.cli.command("gc-storage")
def gc_storage_cmd():
    """Delete storage objects for upload sessions that never got confirmed
    (abandoned presigned/multipart uploads)."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=UPLOAD_SESSION_TTL_SECONDS)
    db = SessionLocal()
    try:
        stale = (
            db.execute(
                select(UploadSession).where(
                    UploadSession.status.in_(["pending", "uploaded"]),
                    UploadSession.created_at < cutoff,
                )
            )
            .scalars()
            .all()
        )
        report = storage.garbage_collect(
            storage.storage_manager.provider, [s.key for s in stale]
        )
        for s in stale:
            s.status = "expired"
        db.commit()
        click.echo(
            f"gc-storage: {len(report.deleted)} deleted, "
            f"{len(report.failed)} failed, {len(stale)} session(s) expired"
        )
    finally:
        db.close()


@app.cli.command("reconcile-storage")
@click.option(
    "--apply",
    is_flag=True,
    help="Actually delete orphaned objects (default: dry-run report only).",
)
def reconcile_storage_cmd(apply):
    """Compare what's actually in storage against what the DB references."""
    db = SessionLocal()
    try:
        known_keys = {
            row[0] for row in db.execute(select(UserFile.path)).all() if row[0]
        }
        report = storage.reconcile(
            storage.storage_manager.provider, known_keys, dry_run=not apply
        )
        click.echo(
            f"orphaned: {len(report.orphaned_keys)}  missing: {len(report.missing_keys)}"
        )
        for k in report.orphaned_keys:
            click.echo(f"  orphan   {k}")
        for k in report.missing_keys:
            click.echo(f"  missing  {k}")
        if apply:
            click.echo(f"deleted: {len(report.deleted)}")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 5: Knowledge Library API
# ══════════════════════════════════════════════════════════════════════════


@app.route("/api/files", methods=["GET"])
@login_required
def list_files():
    """Knowledge Library listing with server-side filtering, sorting, and
    project-scoping.

    Query params (all optional):
      project_id      int     – scope to one project (0 = unassigned)
      kind            str     – "document" | "image" (default: all)
      reading_status  str     – "unread" | "reading" | "read"
      meta_status     str     – "done" | "pending" | "running" | "failed"
      tag             str     – exact tag match (can repeat: ?tag=nlp&tag=cv)
      q               str     – full-text search across name/title/authors/venue
      sort            str     – "recent" (default) | "title" | "authors" |
                                "year" | "reading_status" | "size"
      order           str     – "asc" | "desc" (default: desc for recent/size,
                                asc for everything else)
      limit           int     – max rows (default 200, max 500)
      offset          int     – pagination offset (default 0)
    """
    uid = session["user_id"]
    args = request.args

    # ── parse params ─────────────────────────────────────────────────────
    project_id_raw = args.get("project_id")
    kind = args.get("kind", "").strip().lower() or None
    reading_status = args.get("reading_status", "").strip().lower() or None
    meta_status = args.get("meta_status", "").strip().lower() or None
    tags_filter = args.getlist("tag")  # multi-value
    q = args.get("q", "").strip().lower() or None
    sort = args.get("sort", "recent").strip().lower()
    order = args.get("order", "").strip().lower()  # "" → auto
    try:
        limit = max(1, min(500, int(args.get("limit", 200))))
        offset = max(0, int(args.get("offset", 0)))
    except (TypeError, ValueError):
        limit, offset = 200, 0

    # ── base query ───────────────────────────────────────────────────────
    db = SessionLocal()
    try:
        q_stmt = select(UserFile).where(UserFile.user_id == uid)

        # Project scoping
        if project_id_raw is not None:
            try:
                pid = int(project_id_raw)
                if pid == 0:
                    q_stmt = q_stmt.where(UserFile.project_id.is_(None))
                else:
                    q_stmt = q_stmt.where(UserFile.project_id == pid)
            except (TypeError, ValueError):
                pass

        # Kind filter
        if kind in ("document", "image"):
            q_stmt = q_stmt.where(UserFile.kind == kind)

        # Reading status filter
        if reading_status in ("unread", "reading", "read"):
            q_stmt = q_stmt.where(UserFile.reading_status == reading_status)

        # Meta status filter (e.g. "done" to show only fully processed papers)
        if meta_status in ("pending", "running", "done", "failed"):
            q_stmt = q_stmt.where(UserFile.meta_status == meta_status)

        # Execute and load into memory for Python-side filtering
        # (SQLite doesn't support JSON_CONTAINS; Postgres would let us push
        # this down, but we keep it portable at MVP scale)
        files = db.execute(q_stmt).scalars().all()

        # ── tag filter (Python-side JSON scan) ───────────────────────────
        if tags_filter:
            wanted = {t.lower() for t in tags_filter if t}
            filtered = []
            for f in files:
                try:
                    ftags = {t.lower() for t in json.loads(f.tags or "[]")}
                except Exception:
                    ftags = set()
                if wanted <= ftags:  # all wanted tags must be present
                    filtered.append(f)
            files = filtered

        # ── full-text search (Python-side) ───────────────────────────────
        if q:
            words = q.split()

            def _matches(f):
                haystack = " ".join(
                    filter(
                        None,
                        [
                            f.name,
                            f.title,
                            f.authors,
                            f.venue,
                            f.abstract[:500] if f.abstract else "",
                            " ".join(json.loads(f.tags or "[]")),
                        ],
                    )
                ).lower()
                return all(w in haystack for w in words)

            files = [f for f in files if _matches(f)]

        # ── sort ─────────────────────────────────────────────────────────
        SORT_KEYS = {
            "recent": lambda f: f.created_at or datetime.min,
            "title": lambda f: (f.title or f.name or "").lower(),
            "authors": lambda f: (f.authors or "").lower(),
            "year": lambda f: f.year or "",
            "reading_status": lambda f: {"reading": 0, "unread": 1, "read": 2}.get(
                f.reading_status or "unread", 1
            ),
            "size": lambda f: f.size or 0,
        }
        key_fn = SORT_KEYS.get(sort, SORT_KEYS["recent"])
        reverse = (order == "desc") if order else sort in ("recent", "size")
        files = sorted(files, key=key_fn, reverse=reverse)

        # ── pagination ───────────────────────────────────────────────────
        total = len(files)
        page = files[offset : offset + limit]

        return jsonify(
            {
                "total": total,
                "offset": offset,
                "limit": limit,
                "items": [_file_to_dict(x) for x in page],
            }
        )
    finally:
        db.close()


@app.route("/api/library/tags", methods=["GET"])
@login_required
def library_tags():
    """Return all unique tags the user has applied, with usage counts.

    Optional ?project_id=<id> to scope to one project.
    Response: [{tag, count}] sorted by count desc.
    """
    uid = session["user_id"]
    project_id_raw = request.args.get("project_id")
    db = SessionLocal()
    try:
        q_stmt = select(UserFile).where(
            UserFile.user_id == uid,
            UserFile.tags.isnot(None),
        )
        if project_id_raw is not None:
            try:
                pid = int(project_id_raw)
                q_stmt = q_stmt.where(
                    UserFile.project_id == pid if pid else UserFile.project_id.is_(None)
                )
            except (TypeError, ValueError):
                pass

        files = db.execute(q_stmt).scalars().all()
        counts: dict[str, int] = {}
        for f in files:
            try:
                for t in json.loads(f.tags or "[]"):
                    if t:
                        counts[t] = counts.get(t, 0) + 1
            except Exception:
                pass

        result = sorted(
            [{"tag": t, "count": c} for t, c in counts.items()],
            key=lambda x: -x["count"],
        )
        return jsonify(result)
    finally:
        db.close()


@app.route("/api/library/stats", methods=["GET"])
@login_required
def library_stats():
    """Aggregate counts used by the Research Dashboard (Milestone 8).

    Optional ?project_id=<id> to scope to one project.

    Response:
      total_papers    – documents only
      total_images    – images only
      unread          – reading_status = unread
      reading         – reading_status = reading
      read            – reading_status = read
      analysis_done   – PaperAnalysis rows with status = done
      analysis_pending– rows with status = pending | running
      top_tags        – [{tag, count}] top 5
    """
    uid = session["user_id"]
    project_id_raw = request.args.get("project_id")
    db = SessionLocal()
    try:
        q_stmt = select(UserFile).where(UserFile.user_id == uid)
        if project_id_raw is not None:
            try:
                pid = int(project_id_raw)
                q_stmt = q_stmt.where(
                    UserFile.project_id == pid if pid else UserFile.project_id.is_(None)
                )
            except (TypeError, ValueError):
                pass

        files = db.execute(q_stmt).scalars().all()
        docs = [f for f in files if f.kind == "document"]
        images = [f for f in files if f.kind == "image"]

        rs_counts: dict[str, int] = {"unread": 0, "reading": 0, "read": 0}
        tag_counts: dict[str, int] = {}
        for f in docs:
            rs = f.reading_status or "unread"
            if rs in rs_counts:
                rs_counts[rs] += 1
            try:
                for t in json.loads(f.tags or "[]"):
                    if t:
                        tag_counts[t] = tag_counts.get(t, 0) + 1
            except Exception:
                pass

        # Analysis counts — query PaperAnalysis for the relevant file ids
        doc_ids = [f.id for f in docs]
        analyses_done = 0
        analyses_pending = 0
        if doc_ids:
            pas = (
                db.execute(
                    select(PaperAnalysis).where(PaperAnalysis.file_id.in_(doc_ids))
                )
                .scalars()
                .all()
            )
            analyses_done = sum(1 for p in pas if p.status == "done")
            analyses_pending = sum(1 for p in pas if p.status in ("pending", "running"))

        top_tags = sorted(
            [{"tag": t, "count": c} for t, c in tag_counts.items()],
            key=lambda x: -x["count"],
        )[:5]

        return jsonify(
            {
                "total_papers": len(docs),
                "total_images": len(images),
                "unread": rs_counts["unread"],
                "reading": rs_counts["reading"],
                "read": rs_counts["read"],
                "analysis_done": analyses_done,
                "analysis_pending": analyses_pending,
                "top_tags": top_tags,
            }
        )
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 8: Dashboard API
# ══════════════════════════════════════════════════════════════════════════


@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Single-call summary for the Research Dashboard.

    Returns everything the dashboard needs in one request to avoid
    waterfall fetches on page load.

    Response shape:
      library         – library stats (total_papers, reading/unread/read counts, top_tags)
      recent_papers   – last 5 uploaded documents [{id,name,title,authors,year,
                         reading_status,meta_status,created_at}]
      current_papers  – papers currently being read (reading_status=reading, limit 5)
      recent_chats    – last 5 conversations [{id,title,updated_at,file_id}]
      recent_citations– last 5 citations [{id,title,authors,year}]
      projects        – [{id,name,emoji,paper_count,chat_count}]
    """
    uid = session["user_id"]
    db = SessionLocal()
    try:
        # ── Files ───────────────────────────────────────────────────────────
        all_files = (
            db.execute(select(UserFile).where(UserFile.user_id == uid)).scalars().all()
        )
        docs = [f for f in all_files if f.kind == "document"]
        rs_cnt = {"unread": 0, "reading": 0, "read": 0}
        tag_cnt: dict[str, int] = {}
        for f in docs:
            rs = f.reading_status or "unread"
            if rs in rs_cnt:
                rs_cnt[rs] += 1
            try:
                for t in json.loads(f.tags or "[]"):
                    if t:
                        tag_cnt[t] = tag_cnt.get(t, 0) + 1
            except Exception:
                pass

        def _paper_brief(f):
            return {
                "id": f.id,
                "name": f.name,
                "title": f.title or "",
                "authors": f.authors or "",
                "year": f.year or "",
                "reading_status": f.reading_status or "unread",
                "meta_status": f.meta_status or "pending",
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }

        # Sort by created_at descending for recent papers
        sorted_docs = sorted(
            docs,
            key=lambda f: f.created_at or datetime.min,
            reverse=True,
        )
        recent_papers = [_paper_brief(f) for f in sorted_docs[:5]]
        current_papers = [
            _paper_brief(f)
            for f in sorted_docs
            if (f.reading_status or "unread") == "reading"
        ][:5]

        top_tags = sorted(
            [{"tag": t, "count": c} for t, c in tag_cnt.items()],
            key=lambda x: -x["count"],
        )[:5]

        library = {
            "total_papers": len(docs),
            "unread": rs_cnt["unread"],
            "reading": rs_cnt["reading"],
            "read": rs_cnt["read"],
            "top_tags": top_tags,
        }

        # ── Conversations ────────────────────────────────────────────────────
        convos = (
            db.execute(
                select(Conversation)
                .where(Conversation.user_id == uid)
                .order_by(Conversation.updated_at.desc())
            )
            .scalars()
            .all()
        )
        recent_chats = [
            {
                "id": c.id,
                "title": c.title or "Untitled chat",
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "file_id": c.file_id,
                "project_id": c.project_id,
            }
            for c in convos[:5]
        ]

        # ── Citations ────────────────────────────────────────────────────────
        cites = (
            db.execute(
                select(Citation)
                .where(Citation.user_id == uid)
                .order_by(Citation.created_at.desc())
            )
            .scalars()
            .all()
        )
        recent_citations = [
            {"id": c.id, "title": c.title, "authors": c.authors, "year": c.year}
            for c in cites[:5]
        ]

        # ── Projects ─────────────────────────────────────────────────────────
        projects = (
            db.execute(select(Project).where(Project.user_id == uid)).scalars().all()
        )
        file_proj_cnt = {}
        for f in docs:
            if f.project_id:
                file_proj_cnt[f.project_id] = file_proj_cnt.get(f.project_id, 0) + 1
        convo_proj_cnt = {}
        for c in convos:
            if c.project_id:
                convo_proj_cnt[c.project_id] = convo_proj_cnt.get(c.project_id, 0) + 1

        projects_out = [
            {
                "id": p.id,
                "name": p.name,
                "emoji": p.emoji,
                "paper_count": file_proj_cnt.get(p.id, 0),
                "chat_count": convo_proj_cnt.get(p.id, 0),
            }
            for p in projects
        ]

        return jsonify(
            {
                "library": library,
                "recent_papers": recent_papers,
                "current_papers": current_papers,
                "recent_chats": recent_chats,
                "recent_citations": recent_citations,
                "projects": projects_out,
            }
        )
    finally:
        db.close()


@app.route("/api/files/<int:fid>", methods=["GET"])
@login_required
def get_file(fid):
    """Return full metadata for a single file, including analysis status."""
    db = SessionLocal()
    try:
        x = db.get(UserFile, fid)
        if not x or x.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_file_to_dict(x))
    finally:
        db.close()


@app.route("/api/files/<int:fid>", methods=["PATCH"])
@login_required
def patch_file(fid):
    """Update user-editable metadata: title, authors, year, venue, doi,
    abstract, reading_status, tags.  All fields optional.  Returns the
    full updated file dict so the frontend can replace its cached value."""
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        x = db.get(UserFile, fid)
        if not x or x.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404

        if "title" in data:
            x.title = str(data["title"])[:500]
        if "authors" in data:
            x.authors = str(data["authors"])[:1000]
        if "year" in data:
            y = _re_meta.search(r"(19|20)\d{2}", str(data["year"]) or "")
            x.year = y.group(0) if y else ""
        if "venue" in data:
            x.venue = str(data["venue"])[:300]
        if "doi" in data:
            x.doi = str(data["doi"])[:200]
        if "abstract" in data:
            x.abstract = str(data["abstract"])[:8000]
        if "reading_status" in data:
            rs = data["reading_status"]
            if rs in ("unread", "reading", "read"):
                x.reading_status = rs
        if "tags" in data:
            tags = [str(t)[:80] for t in (data["tags"] or []) if t][:30]
            x.tags = json.dumps(tags)

        db.commit()
        return jsonify(_file_to_dict(x))
    finally:
        db.close()


@app.route("/api/files/<int:fid>/analysis", methods=["GET"])
@login_required
def get_analysis(fid):
    """Return the cached paper analysis for one file.

    Possible status values the frontend should handle:
      pending  – file was just uploaded; background job not started yet
      running  – model call in progress
      done     – analysis ready; 'data' contains the 14 fields
      failed   – something went wrong; 'error' has details
      none     – file is not a text document (image, scanned PDF, etc.)
    """
    db = SessionLocal()
    try:
        uf = db.get(UserFile, fid)
        if not uf or uf.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404

        if uf.kind == "image" or uf.text_len == 0:
            return jsonify(
                {
                    "file_id": fid,
                    "status": "none",
                    "error": "no text content",
                    "model": "",
                    "data": {},
                    "updated_at": None,
                }
            )

        pa = db.execute(
            select(PaperAnalysis).where(PaperAnalysis.file_id == fid)
        ).scalar_one_or_none()

        if pa is None:
            # No record yet — start analysis now and return pending
            uf2 = db.get(UserFile, fid)
            h = uf2.content_hash or ""
            if h:
                text = ""
            else:
                with storage.local_copy(uf2.path) as local_path:
                    text = extract_text(local_path, uf2.mime, uf2.name)
            if not h and text:
                h = _sha256(text)
                uf2.content_hash = h
                db.commit()
            trigger_paper_analysis(fid, text, h)
            return jsonify(
                {
                    "file_id": fid,
                    "status": "pending",
                    "error": "",
                    "model": "",
                    "data": {},
                    "updated_at": None,
                }
            )

        return jsonify(_analysis_to_dict(pa))
    finally:
        db.close()


@app.route("/api/files/<int:fid>/analysis/refresh", methods=["POST"])
@login_required
def refresh_analysis(fid):
    """Force-regenerate the analysis for a file, ignoring the cached version.

    Useful after the user edits a document or when the first run failed.
    The response immediately returns {status: "running"} while the background
    job proceeds; the frontend should poll GET /analysis until status=='done'.
    """
    db = SessionLocal()
    try:
        uf = db.get(UserFile, fid)
        if not uf or uf.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        if uf.kind == "image" or uf.text_len == 0:
            return jsonify({"error": "no_text_content"}), 400

        # Wipe the cached hash so the worker doesn't short-circuit
        pa = db.execute(
            select(PaperAnalysis).where(PaperAnalysis.file_id == fid)
        ).scalar_one_or_none()
        if pa:
            pa.content_hash = ""
            pa.status = "pending"
            db.commit()

        with storage.local_copy(uf.path) as local_path:
            text = extract_text(local_path, uf.mime, uf.name)
        h = _sha256(text) if text else ""
        trigger_paper_analysis(fid, text, h)
        return jsonify({"ok": True, "status": "running"})
    finally:
        db.close()


@app.route("/api/files/<int:fid>/raw")
@login_required
def file_raw(fid):
    db = SessionLocal()
    try:
        x = db.get(UserFile, fid)
        if not x or x.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        url = storage.presigned_url(
            x.path, x.name, x.mime or "application/octet-stream"
        )
        return redirect(url)
    finally:
        db.close()


@app.route("/api/files/<int:fid>", methods=["DELETE"])
@login_required
def delete_file(fid):
    db = SessionLocal()
    try:
        x = db.get(UserFile, fid)
        if not x or x.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        storage.delete(x.path)
        db.delete(x)
        _adjust_storage_usage(
            db, session["user_id"], delta_bytes=-(x.size or 0), delta_files=-1
        )
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 10: Notes API
# ══════════════════════════════════════════════════════════════════════════


def _note_to_dict(n):
    """Serialise a Note row to the public API shape."""
    return {
        "id": n.id,
        "title": n.title or "",
        "content": n.content or "",
        "project_id": n.project_id,
        "file_id": n.file_id,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@app.route("/api/notes", methods=["GET"])
@login_required
def list_notes():
    """List notes for the current user.

    Query params (all optional):
      project_id  int   – filter to one project (0 = unassigned)
      file_id     int   – filter to one paper (paper-level notes)
      q           str   – substring search in title + content
      limit       int   – max rows (default 200, max 500)
      offset      int   – pagination offset
    """
    uid = session["user_id"]
    args = request.args

    project_id_raw = args.get("project_id")
    file_id_raw = args.get("file_id", type=int)
    q = args.get("q", "").strip().lower() or None
    try:
        limit = max(1, min(500, int(args.get("limit", 200))))
        offset = max(0, int(args.get("offset", 0)))
    except (TypeError, ValueError):
        limit, offset = 200, 0

    db = SessionLocal()
    try:
        stmt = select(Note).where(Note.user_id == uid)

        if project_id_raw is not None:
            try:
                pid = int(project_id_raw)
                stmt = stmt.where(
                    Note.project_id == pid if pid else Note.project_id.is_(None)
                )
            except (TypeError, ValueError):
                pass

        if file_id_raw is not None:
            stmt = stmt.where(Note.file_id == file_id_raw)

        notes = db.execute(stmt.order_by(Note.updated_at.desc())).scalars().all()

        # Full-text search (Python side for SQLite portability)
        if q:
            notes = [
                n
                for n in notes
                if q in (n.title or "").lower() or q in (n.content or "").lower()
            ]

        total = len(notes)
        page = notes[offset : offset + limit]

        return jsonify(
            {
                "total": total,
                "offset": offset,
                "limit": limit,
                "items": [_note_to_dict(n) for n in page],
            }
        )
    finally:
        db.close()


@app.route("/api/notes", methods=["POST"])
@login_required
def create_note():
    """Create a new note.

    Body:
      title       str   – note heading (optional, defaults to '')
      content     str   – note body (required, min 1 char after strip)
      project_id  int   – scope to a project (nullable)
      file_id     int   – attach to a paper (nullable)
    """
    data = request.get_json(silent=True) or {}
    uid = session["user_id"]

    content = str(data.get("content") or "").strip()
    if not content:
        return (
            jsonify(
                {"error": "content_required", "detail": "Note content cannot be empty."}
            ),
            400,
        )

    title = str(data.get("title") or "")[:300]
    project_id = data.get("project_id")
    file_id = data.get("file_id")

    db = SessionLocal()
    try:
        # Validate project ownership
        if project_id:
            p = db.get(Project, project_id)
            if not p or p.user_id != uid:
                project_id = None

        # Validate file ownership
        if file_id:
            f = db.get(UserFile, file_id)
            if not f or f.user_id != uid:
                file_id = None
            elif not project_id and f.project_id:
                project_id = f.project_id  # inherit from paper

        n = Note(
            user_id=uid,
            title=title,
            content=content[:50000],
            project_id=project_id,
            file_id=file_id,
        )
        db.add(n)
        db.commit()
        return jsonify(_note_to_dict(n)), 201
    finally:
        db.close()


@app.route("/api/notes/<int:nid>", methods=["GET"])
@login_required
def get_note(nid):
    db = SessionLocal()
    try:
        n = db.get(Note, nid)
        if not n or n.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_note_to_dict(n))
    finally:
        db.close()


@app.route("/api/notes/<int:nid>", methods=["PATCH"])
@login_required
def update_note(nid):
    """Update title and/or content of a note. Returns the full updated note."""
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        n = db.get(Note, nid)
        if not n or n.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        if "title" in data:
            n.title = str(data["title"] or "")[:300]
        if "content" in data:
            n.content = str(data["content"] or "")[:50000]
        # Allow re-scoping
        if "project_id" in data:
            pid = data["project_id"]
            if pid is None:
                n.project_id = None
            else:
                p = db.get(Project, pid)
                if p and p.user_id == session["user_id"]:
                    n.project_id = pid
        if "file_id" in data:
            fid = data["file_id"]
            if fid is None:
                n.file_id = None
            else:
                f = db.get(UserFile, fid)
                if f and f.user_id == session["user_id"]:
                    n.file_id = fid
        # Manually bump updated_at (SQLite onupdate doesn't fire on session.commit)
        n.updated_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify(_note_to_dict(n))
    finally:
        db.close()


@app.route("/api/notes/<int:nid>", methods=["DELETE"])
@login_required
def delete_note(nid):
    db = SessionLocal()
    try:
        n = db.get(Note, nid)
        if not n or n.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        db.delete(n)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ------------------------------------------------------------------ API: citations
def bibtex_entry(c):
    first_author = (c.authors or "anon").split(";")[0].split(",")[0].strip()
    key = "".join(ch for ch in first_author if ch.isalnum()).lower() + (c.year or "")
    fields = []
    if c.authors:
        fields.append(f"  author = {{{c.authors}}}")
    if c.title:
        fields.append(f"  title = {{{c.title}}}")
    if c.venue:
        fields.append(f"  journal = {{{c.venue}}}")
    if c.year:
        fields.append(f"  year = {{{c.year}}}")
    if c.doi:
        fields.append(f"  doi = {{{c.doi}}}")
    if c.url:
        fields.append(f"  url = {{{c.url}}}")
    return "@article{" + (key or "ref") + ",\n" + ",\n".join(fields) + "\n}"


def apa_entry(c) -> str:
    """Format a Citation row as APA 7th edition.

    Pattern: Last, F. M., & Last, F. M. (Year). Title. *Venue*. https://doi.org/DOI
    """
    # Build author string: "Last, F." parts joined with ", " and final " & "
    raw_authors = [a.strip() for a in (c.authors or "").split(";") if a.strip()]
    if not raw_authors:
        author_str = "Unknown Author"
    elif len(raw_authors) == 1:
        author_str = raw_authors[0]
    elif len(raw_authors) <= 20:
        author_str = ", ".join(raw_authors[:-1]) + ", & " + raw_authors[-1]
    else:
        # More than 20 authors: first 19, ellipsis, last
        author_str = ", ".join(raw_authors[:19]) + ", ... " + raw_authors[-1]

    year_part = f"({c.year}). " if c.year else ""
    title_part = f"{c.title}. " if c.title else ""
    venue_part = f"*{c.venue}*. " if c.venue else ""
    doi_part = f"https://doi.org/{c.doi}" if c.doi else (c.url or "")

    return (
        f"{author_str}. {year_part}{title_part}{venue_part}{doi_part}".strip().rstrip(
            "."
        )
    )


def ieee_entry(c) -> str:
    """Format a Citation row as IEEE style.

    Pattern: [n] F. Last and F. Last, "Title," *Venue*, Year. doi: DOI
    """
    raw_authors = [a.strip() for a in (c.authors or "").split(";") if a.strip()]

    def _to_ieee_name(author: str) -> str:
        """Convert 'Last, First' → 'F. Last'."""
        parts = [p.strip() for p in author.split(",", 1)]
        if len(parts) == 2:
            last, first = parts
            initials = ". ".join(w[0] for w in first.split() if w) + "."
            return f"{initials} {last}"
        return author

    if not raw_authors:
        author_str = "Unknown"
    elif len(raw_authors) == 1:
        author_str = _to_ieee_name(raw_authors[0])
    elif len(raw_authors) <= 3:
        names = [_to_ieee_name(a) for a in raw_authors]
        author_str = " and ".join(names)
    else:
        author_str = _to_ieee_name(raw_authors[0]) + " et al."

    title_part = f'"{c.title}," ' if c.title else ""
    venue_part = f"*{c.venue}*, " if c.venue else ""
    year_part = f"{c.year}. " if c.year else ""
    doi_part = f"doi: {c.doi}" if c.doi else (c.url or "")

    return f"{author_str}, {title_part}{venue_part}{year_part}{doi_part}".strip()


def format_citation(c, fmt: str = "bibtex") -> str:
    """Dispatch to the appropriate formatter."""
    if fmt == "apa":
        return apa_entry(c)
    if fmt == "ieee":
        return ieee_entry(c)
    return bibtex_entry(c)


def _citation_to_dict(c, fmt: str = "bibtex") -> dict:
    """Unified serialiser for Citation rows."""
    return {
        "id": c.id,
        "authors": c.authors or "",
        "title": c.title or "",
        "year": c.year or "",
        "venue": c.venue or "",
        "doi": c.doi or "",
        "url": c.url or "",
        "notes": c.notes or "",
        "project_id": c.project_id,
        "bibtex": bibtex_entry(c),
        "apa": apa_entry(c),
        "ieee": ieee_entry(c),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 13: Citation Manager (APA/IEEE/BibTeX)
# ══════════════════════════════════════════════════════════════════════════


@app.route("/api/citations", methods=["GET"])
@login_required
def list_citations():
    """List citations with optional project_id filter.

    Query params:
      project_id  int   – scope to one project (0 = unassigned)
      q           str   – substring search in title/authors/venue
    """
    uid = session["user_id"]
    args = request.args
    project_id_raw = args.get("project_id")
    q = args.get("q", "").strip().lower() or None

    db = SessionLocal()
    try:
        stmt = select(Citation).where(Citation.user_id == uid)
        if project_id_raw is not None:
            try:
                pid = int(project_id_raw)
                stmt = stmt.where(
                    Citation.project_id == pid if pid else Citation.project_id.is_(None)
                )
            except (TypeError, ValueError):
                pass
        cits = db.execute(stmt.order_by(Citation.created_at.desc())).scalars().all()
        if q:
            cits = [
                c
                for c in cits
                if q in (c.title or "").lower()
                or q in (c.authors or "").lower()
                or q in (c.venue or "").lower()
            ]
        return jsonify([_citation_to_dict(c) for c in cits])
    finally:
        db.close()


@app.route("/api/citations", methods=["POST"])
@login_required
def create_citation():
    d = request.get_json(silent=True) or {}
    uid = session["user_id"]
    db = SessionLocal()
    try:
        # Validate project ownership
        project_id = d.get("project_id")
        if project_id:
            p = db.get(Project, project_id)
            if not p or p.user_id != uid:
                project_id = None
        c = Citation(
            user_id=uid,
            project_id=project_id,
            authors=str(d.get("authors", ""))[:500],
            title=str(d.get("title", ""))[:500],
            year=str(d.get("year", ""))[:10],
            venue=str(d.get("venue", ""))[:300],
            doi=str(d.get("doi", ""))[:200],
            url=str(d.get("url", ""))[:600],
            notes=str(d.get("notes", ""))[:2000],
        )
        db.add(c)
        db.commit()
        return jsonify(_citation_to_dict(c)), 201
    finally:
        db.close()


@app.route("/api/citations/<int:cid>", methods=["GET"])
@login_required
def get_citation(cid):
    db = SessionLocal()
    try:
        c = db.get(Citation, cid)
        if not c or c.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_citation_to_dict(c))
    finally:
        db.close()


@app.route("/api/citations/<int:cid>", methods=["PATCH"])
@login_required
def update_citation(cid):
    """Edit any field of an existing citation. Returns full updated dict."""
    d = request.get_json(silent=True) or {}
    uid = session["user_id"]
    db = SessionLocal()
    try:
        c = db.get(Citation, cid)
        if not c or c.user_id != uid:
            return jsonify({"error": "not_found"}), 404
        for field, maxlen in (
            ("authors", 500),
            ("title", 500),
            ("year", 10),
            ("venue", 300),
            ("doi", 200),
            ("url", 600),
            ("notes", 2000),
        ):
            if field in d:
                setattr(c, field, str(d[field] or "")[:maxlen])
        if "project_id" in d:
            pid = d["project_id"]
            if pid is None:
                c.project_id = None
            else:
                p = db.get(Project, pid)
                if p and p.user_id == uid:
                    c.project_id = pid
        db.commit()
        return jsonify(_citation_to_dict(c))
    finally:
        db.close()


@app.route("/api/citations/<int:cid>", methods=["DELETE"])
@login_required
def delete_citation(cid):
    db = SessionLocal()
    try:
        c = db.get(Citation, cid)
        if not c or c.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        db.delete(c)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/citations/from-paper/<int:fid>", methods=["POST"])
@login_required
def citation_from_paper(fid):
    """Auto-create a citation from a paper's extracted metadata.

    Uses UserFile.title/authors/year/venue/doi to pre-populate the
    Citation row. Returns the created citation so the frontend can
    display it immediately. Idempotent: if a citation with the same
    title already exists for this user, returns the existing one.
    """
    uid = session["user_id"]
    db = SessionLocal()
    try:
        uf = db.get(UserFile, fid)
        if not uf or uf.user_id != uid:
            return jsonify({"error": "not_found"}), 404
        if not uf.title:
            return (
                jsonify(
                    {
                        "error": "no_metadata",
                        "detail": "This paper has no extracted title yet. "
                        "Wait for metadata extraction to complete.",
                    }
                ),
                400,
            )

        # Idempotency: don't duplicate if already saved
        existing = db.execute(
            select(Citation).where(
                Citation.user_id == uid,
                Citation.title == uf.title,
            )
        ).scalar_one_or_none()
        if existing:
            return jsonify({**_citation_to_dict(existing), "existing": True})

        body = request.get_json(silent=True) or {}
        project_id = body.get("project_id") or uf.project_id

        c = Citation(
            user_id=uid,
            project_id=project_id,
            title=uf.title[:500],
            authors=(uf.authors or "")[:500],
            year=(uf.year or "")[:10],
            venue=(uf.venue or "")[:300],
            doi=(uf.doi or "")[:200],
            url=(f"https://doi.org/{uf.doi}" if uf.doi else "")[:600],
            notes="",
        )
        db.add(c)
        db.commit()
        return jsonify({**_citation_to_dict(c), "existing": False}), 201
    finally:
        db.close()


@app.route("/api/citations/export")
@login_required
def export_citations():
    """Export citations in BibTeX (default), APA, or IEEE format.

    Query params:
      format      str   – "bibtex" (default) | "apa" | "ieee"
      project_id  int   – scope to one project
    """
    uid = session["user_id"]
    fmt = request.args.get("format", "bibtex").lower()
    project_id_raw = request.args.get("project_id")

    db = SessionLocal()
    try:
        stmt = select(Citation).where(Citation.user_id == uid)
        if project_id_raw is not None:
            try:
                pid = int(project_id_raw)
                stmt = stmt.where(
                    Citation.project_id == pid if pid else Citation.project_id.is_(None)
                )
            except (TypeError, ValueError):
                pass
        cits = db.execute(stmt.order_by(Citation.created_at)).scalars().all()

        if fmt in ("apa", "ieee"):
            lines = [format_citation(c, fmt) for c in cits]
            blob = "\n\n".join(lines)
            mime = "text/plain"
            fname = f"references-{fmt}.txt"
        else:
            blob = "\n\n".join(bibtex_entry(c) for c in cits)
            mime = "application/x-bibtex"
            fname = "references.bib"

        return send_file(
            io.BytesIO(blob.encode("utf-8")),
            mimetype=mime,
            as_attachment=True,
            download_name=fname,
        )
    finally:
        db.close()


# ------------------------------------------------------------------ API: projects
@app.route("/api/projects", methods=["GET"])
@login_required
def list_projects():
    db = SessionLocal()
    try:
        projs = (
            db.execute(
                select(Project)
                .where(Project.user_id == session["user_id"])
                .order_by(Project.created_at)
            )
            .scalars()
            .all()
        )
        return jsonify(
            [
                {
                    "id": p.id,
                    "name": p.name,
                    "emoji": p.emoji,
                    "description": p.description or "",
                    "instructions": p.instructions or "",
                }
                for p in projs
            ]
        )
    finally:
        db.close()


@app.route("/api/projects", methods=["POST"])
@login_required
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()[:100]
    if not name:
        return jsonify({"error": "name_required"}), 400
    db = SessionLocal()
    try:
        p = Project(
            user_id=session["user_id"],
            name=name,
            emoji=(data.get("emoji") or "📁")[:16],
            description=(data.get("description") or "")[:2000],
            instructions=(data.get("instructions") or "")[:4000],
        )
        db.add(p)
        db.commit()
        return jsonify(
            {
                "id": p.id,
                "name": p.name,
                "emoji": p.emoji,
                "description": p.description or "",
                "instructions": p.instructions,
            }
        )
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 9: Project detail + scoped stats
# ══════════════════════════════════════════════════════════════════════════


@app.route("/api/projects/<int:pid>", methods=["GET"])
@login_required
def get_project(pid):
    """Full project detail with scoped counts (papers, chats, memories).

    Used by the Project Detail Page to populate the overview without
    requiring the frontend to aggregate from multiple list queries.
    """
    uid = session["user_id"]
    db = SessionLocal()
    try:
        p = db.get(Project, pid)
        if not p or p.user_id != uid:
            return jsonify({"error": "not_found"}), 404

        # Scoped counts
        paper_count = (
            db.execute(
                select(UserFile).where(
                    UserFile.user_id == uid,
                    UserFile.project_id == pid,
                    UserFile.kind == "document",
                )
            )
            .scalars()
            .all()
        )

        chat_count = (
            db.execute(
                select(Conversation).where(
                    Conversation.user_id == uid, Conversation.project_id == pid
                )
            )
            .scalars()
            .all()
        )

        memory_count = (
            db.execute(
                select(Memory).where(Memory.user_id == uid, Memory.project_id == pid)
            )
            .scalars()
            .all()
        )

        # Reading status breakdown for papers in this project
        rs_counts = {"unread": 0, "reading": 0, "read": 0}
        for f in paper_count:
            rs = f.reading_status or "unread"
            if rs in rs_counts:
                rs_counts[rs] += 1

        return jsonify(
            {
                "id": p.id,
                "name": p.name,
                "emoji": p.emoji,
                "description": p.description or "",
                "instructions": p.instructions or "",
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "stats": {
                    "papers": len(paper_count),
                    "chats": len(chat_count),
                    "memories": len(memory_count),
                    "unread": rs_counts["unread"],
                    "reading": rs_counts["reading"],
                    "read": rs_counts["read"],
                },
            }
        )
    finally:
        db.close()


@app.route("/api/projects/<int:pid>", methods=["PATCH"])
@login_required
def update_project(pid):
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        p = db.get(Project, pid)
        if not p or p.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        if "name" in data:
            p.name = str(data["name"]).strip()[:100] or p.name
        if "emoji" in data:
            p.emoji = str(data["emoji"])[:16] or p.emoji
        if "description" in data:
            p.description = str(data["description"])[:2000]
        if "instructions" in data:
            p.instructions = str(data["instructions"])[:4000]
        db.commit()
        return jsonify(
            {
                "id": p.id,
                "name": p.name,
                "emoji": p.emoji,
                "description": p.description or "",
                "instructions": p.instructions or "",
            }
        )
    finally:
        db.close()


@app.route("/api/projects/<int:pid>", methods=["DELETE"])
@login_required
def delete_project(pid):
    db = SessionLocal()
    try:
        p = db.get(Project, pid)
        if not p or p.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        for c in db.execute(
            select(Conversation).where(Conversation.project_id == pid)
        ).scalars():
            c.project_id = None
        for m in db.execute(select(Memory).where(Memory.project_id == pid)).scalars():
            db.delete(m)
        db.delete(p)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/conversations", methods=["GET"])
@login_required
def list_conversations():
    db = SessionLocal()
    try:
        convos = (
            db.execute(
                select(Conversation)
                .where(Conversation.user_id == session["user_id"])
                .order_by(Conversation.updated_at.desc())
            )
            .scalars()
            .all()
        )
        return jsonify(
            [
                {
                    "id": c.id,
                    "title": c.title,
                    "model": c.model,
                    "project_id": c.project_id,
                    "file_id": c.file_id,
                }
                for c in convos
            ]
        )
    finally:
        db.close()


VALID_REASONING_EFFORTS = ("low", "medium", "high")


def apply_conversation_settings(c, data):
    """Shared temperature/reasoning_effort/memory_enabled handling for
    create/update — nullable fields reset to provider default when passed
    explicitly as null."""
    if "temperature" in data:
        t = data["temperature"]
        c.temperature = None if t is None else max(0.0, min(2.0, float(t)))
    if "reasoning_effort" in data:
        r = data["reasoning_effort"]
        c.reasoning_effort = r if r in VALID_REASONING_EFFORTS else None
    if "memory_enabled" in data:
        c.memory_enabled = 1 if data["memory_enabled"] else 0


def conversation_settings_json(c):
    return {
        "temperature": c.temperature,
        "reasoning_effort": c.reasoning_effort,
        "memory_enabled": (
            bool(c.memory_enabled) if c.memory_enabled is not None else True
        ),
    }


@app.route("/api/conversations", methods=["POST"])
@login_required
def create_conversation():
    data = request.get_json(silent=True) or {}
    model = data.get("model") or DEFAULT_MODEL
    if model not in get_models():
        model = DEFAULT_MODEL
    project_id = data.get("project_id")
    file_id = data.get("file_id")  # M7: paper chat
    db = SessionLocal()
    try:
        if project_id:
            p = db.get(Project, project_id)
            if not p or p.user_id != session["user_id"]:
                project_id = None

        # Validate file ownership; inherit project from the paper if not given
        paper_title = None
        if file_id:
            uf = db.get(UserFile, file_id)
            if not uf or uf.user_id != session["user_id"]:
                file_id = None
            else:
                paper_title = uf.title or uf.name or None
                if not project_id and uf.project_id:
                    project_id = uf.project_id

        c = Conversation(
            user_id=session["user_id"],
            model=model,
            project_id=project_id,
            file_id=file_id,
        )
        # Give paper chats a meaningful title immediately so the sidebar shows
        # something useful before the first AI turn generates an auto-title.
        if paper_title and file_id:
            c.title = f"Chat: {paper_title}"[:200]
            c.title_generated = 0  # let the first turn overwrite with a better one
        apply_conversation_settings(c, data)
        db.add(c)
        db.commit()
        return jsonify(
            {
                "id": c.id,
                "title": c.title,
                "model": c.model,
                "project_id": c.project_id,
                "file_id": c.file_id,
                **conversation_settings_json(c),
            }
        )
    finally:
        db.close()


@app.route("/api/conversations/<int:cid>", methods=["GET"])
@login_required
def get_conversation(cid):
    db = SessionLocal()
    try:
        c = db.get(Conversation, cid)
        if not c or c.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        return jsonify(
            {
                "id": c.id,
                "title": c.title,
                "model": c.model,
                "project_id": c.project_id,
                "file_id": c.file_id,  # M7: paper chat scope
                **conversation_settings_json(c),
                "messages": [
                    {
                        "id": m.id,
                        "role": m.role,
                        "content": m.content,
                        "sources": json.loads(m.sources) if m.sources else [],
                        "attachments": (
                            json.loads(m.attachments) if m.attachments else []
                        ),
                    }
                    for m in c.messages
                ],
            }
        )
    finally:
        db.close()


@app.route("/api/conversations/<int:cid>", methods=["PATCH"])
@login_required
def update_conversation(cid):
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        c = db.get(Conversation, cid)
        if not c or c.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        if "title" in data:
            c.title = str(data["title"])[:200]
            c.title_generated = 1
        if "model" in data and data["model"] in get_models():
            c.model = data["model"]
        apply_conversation_settings(c, data)
        if "project_id" in data:
            pid = data["project_id"]
            if pid is None:
                c.project_id = None
            else:
                p = db.get(Project, pid)
                if p and p.user_id == session["user_id"]:
                    c.project_id = pid
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


def _remove_file_row(db, uf):
    """Delete a UserFile completely: its chunks, its R2 object, and the row."""
    storage.delete(uf.path)
    db.execute(delete(Chunk).where(Chunk.file_id == uf.id))
    db.delete(uf)


def _purge_conversation(db, convo):
    """Delete a conversation, its messages (ORM cascade), and its
    conversation-only files/embeddings. Files also attached to a project are
    kept (just detached from the chat)."""
    for uf in (
        db.execute(select(UserFile).where(UserFile.conversation_id == convo.id))
        .scalars()
        .all()
    ):
        if uf.project_id:
            uf.conversation_id = None
        else:
            _remove_file_row(db, uf)
    db.delete(convo)


@app.route("/api/conversations/<int:cid>", methods=["DELETE"])
@login_required
def delete_conversation(cid):
    db = SessionLocal()
    try:
        c = db.get(Conversation, cid)
        if not c or c.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        _purge_conversation(db, c)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/conversations/delete", methods=["POST"])
@login_required
def bulk_delete_conversations():
    """Delete several chats at once, or all of them (`{"all": true}`)."""
    data = request.get_json(silent=True) or {}
    uid = session["user_id"]
    db = SessionLocal()
    try:
        q = select(Conversation).where(Conversation.user_id == uid)
        if not data.get("all"):
            ids = [int(i) for i in (data.get("ids") or [])]
            if not ids:
                return jsonify({"error": "no_ids"}), 400
            q = q.where(Conversation.id.in_(ids))
        convos = db.execute(q).scalars().all()
        for c in convos:
            _purge_conversation(db, c)
        db.commit()
        log_security_event(
            "chats_deleted", user=uid, count=len(convos), all=bool(data.get("all"))
        )
        return jsonify({"ok": True, "deleted": len(convos)})
    finally:
        db.close()


# ------------------------------------------------------------------ export
def _role_label(role):
    return {
        "user": "You",
        "assistant": "Assistant",
        "developer": "System",
        "system": "System",
    }.get(role, role.title())


def _collect_export(db, uid, conversation_id=None):
    q = select(Conversation).where(Conversation.user_id == uid)
    if conversation_id:
        q = q.where(Conversation.id == conversation_id)
    convos = db.execute(q.order_by(Conversation.created_at)).scalars().all()
    data = []
    for c in convos:
        msgs = [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "attachments": json.loads(m.attachments) if m.attachments else [],
                "sources": json.loads(m.sources) if m.sources else [],
            }
            for m in c.messages
        ]
        data.append(
            {
                "id": c.id,
                "title": c.title or "Untitled",
                "model": c.model,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "messages": msgs,
            }
        )
    cites = (
        db.execute(
            select(Citation)
            .where(Citation.user_id == uid)
            .order_by(Citation.created_at)
        )
        .scalars()
        .all()
    )
    cite_list = [
        {
            "authors": ct.authors,
            "title": ct.title,
            "year": ct.year,
            "venue": ct.venue,
            "doi": ct.doi,
            "url": ct.url,
        }
        for ct in cites
    ]
    return data, cite_list


def _fmt_cite(ct):
    bits = [
        b
        for b in [
            ct.get("authors"),
            f"({ct['year']})" if ct.get("year") else "",
            ct.get("title"),
            ct.get("venue"),
            ct.get("doi"),
            ct.get("url"),
        ]
        if b
    ]
    return ". ".join(bits)


def _export_markdown(data, cites, user, plain=False):
    b = "" if plain else "**"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"{'' if plain else '# '}Chat export — {user['name']}",
        f"Exported {stamp}",
        "",
    ]
    for c in data:
        lines += [
            "",
            f"{'' if plain else '## '}{c['title']}",
            f"{c['created_at']} · {c['model']}",
            "",
        ]
        for m in c["messages"]:
            if m["role"] == "developer":
                continue
            who = _role_label(m["role"])
            att = ""
            if m["attachments"]:
                att = (
                    " (attached: "
                    + ", ".join(a.get("name", "") for a in m["attachments"])
                    + ")"
                )
            lines += [f"{b}{who}{att}:{b}", "", m["content"], ""]
    if cites:
        lines += ["", f"{'' if plain else '## '}Citations", ""]
        lines += [("- " if not plain else "• ") + _fmt_cite(ct) for ct in cites]
    return "\n".join(lines)


def _export_docx(data, cites, user):
    import docx

    d = docx.Document()
    d.add_heading(f"Chat export — {user['name']}", 0)
    d.add_paragraph(datetime.now(timezone.utc).strftime("Exported %Y-%m-%d %H:%M UTC"))
    for c in data:
        d.add_heading(c["title"], level=1)
        meta = d.add_paragraph(f"{c['created_at']} · {c['model']}")
        meta.runs[0].italic = True
        for m in c["messages"]:
            if m["role"] == "developer":
                continue
            p = d.add_paragraph()
            r = p.add_run(f"{_role_label(m['role'])}: ")
            r.bold = True
            p.add_run(m["content"])
            if m["attachments"]:
                names = ", ".join(a.get("name", "") for a in m["attachments"])
                a = d.add_paragraph(f"Attached: {names}")
                a.runs[0].italic = True
    if cites:
        d.add_heading("Citations", level=1)
        for ct in cites:
            d.add_paragraph(_fmt_cite(ct), style="List Bullet")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _text_to_pdf(title, body):
    """Simple word-wrapped, paginated PDF built with PyMuPDF (no extra deps)."""
    import fitz

    W, H, margin, fs, lh = 595.0, 842.0, 50.0, 10.0, 14.0  # A4
    font = fitz.Font("helv")
    max_w = W - 2 * margin
    doc = fitz.open()

    def wrap(line):
        if not line:
            return [""]
        words, out, cur = line.split(" "), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if font.text_length(trial, fs) <= max_w or not cur:
                cur = trial
            else:
                out.append(cur)
                cur = w
        out.append(cur)
        return out

    rows = [(title, 15.0)]
    rows.append(("", fs))
    for raw in body.split("\n"):
        for wl in wrap(raw.replace("\t", "    ")):
            rows.append((wl, fs))

    page = doc.new_page(width=W, height=H)
    y = margin
    for txt, size in rows:
        step = 22.0 if size > 12 else lh
        if y + step > H - margin:
            page = doc.new_page(width=W, height=H)
            y = margin
        try:
            page.insert_text((margin, y), txt, fontsize=size, fontname="helv")
        except Exception:
            page.insert_text(
                (margin, y),
                txt.encode("latin-1", "replace").decode("latin-1"),
                fontsize=size,
                fontname="helv",
            )
        y += step
    out = doc.tobytes()
    doc.close()
    return out


@app.route("/api/export")
@login_required
@limiter.limit("60 per hour")
def export_data():
    fmt = (request.args.get("format") or "json").lower()
    conversation_id = request.args.get("conversation_id", type=int)
    uid = session["user_id"]
    db = SessionLocal()
    try:
        user = db.get(User, uid)
        if conversation_id:
            c = db.get(Conversation, conversation_id)
            if not c or c.user_id != uid:
                return jsonify({"error": "not_found"}), 404
        uinfo = {"name": user.name, "email": user.email}
        data, cites = _collect_export(db, uid, conversation_id)
    finally:
        db.close()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    base = f"personal-ai-export-{stamp}"
    title = f"Chat export — {uinfo['name']}"

    if fmt == "json":
        payload = json.dumps(
            {
                "user": uinfo,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "conversations": data,
                "citations": cites,
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        return _download(payload, base + ".json", "application/json")
    if fmt in ("md", "markdown"):
        return _download(
            _export_markdown(data, cites, uinfo).encode("utf-8"),
            base + ".md",
            "text/markdown",
        )
    if fmt == "txt":
        return _download(
            _export_markdown(data, cites, uinfo, plain=True).encode("utf-8"),
            base + ".txt",
            "text/plain",
        )
    if fmt == "docx":
        return _download(
            _export_docx(data, cites, uinfo),
            base + ".docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    if fmt == "pdf":
        body = _export_markdown(data, cites, uinfo, plain=True)
        return _download(_text_to_pdf(title, body), base + ".pdf", "application/pdf")
    return (
        jsonify(
            {"error": "bad_format", "detail": "format must be json|md|txt|docx|pdf"}
        ),
        400,
    )


def _download(payload, filename, mimetype):
    return send_file(
        io.BytesIO(payload),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


# ------------------------------------------------------------------ delete account
@app.route("/api/account", methods=["DELETE"])
@login_required
@limiter.limit("5 per hour")
def delete_account():
    uid = session["user_id"]
    db = SessionLocal()
    try:
        user = db.get(User, uid)
        if not user:
            return jsonify({"error": "not_found"}), 404
        # Files (chunks + on-disk blobs)
        for uf in (
            db.execute(select(UserFile).where(UserFile.user_id == uid)).scalars().all()
        ):
            _remove_file_row(db, uf)
        # Conversations (messages cascade), memories, citations, projects
        for conv in (
            db.execute(select(Conversation).where(Conversation.user_id == uid))
            .scalars()
            .all()
        ):
            db.delete(conv)
        db.execute(delete(Memory).where(Memory.user_id == uid))
        db.execute(delete(Citation).where(Citation.user_id == uid))
        db.execute(delete(Project).where(Project.user_id == uid))
        db.delete(user)
        db.commit()
    finally:
        db.close()
    log_security_event("account_deleted", user=uid)
    session.clear()
    return jsonify({"ok": True})


# ------------------------------------------------------------------ support
SUPPORT_CATEGORIES = {"general", "bug", "feature", "account"}


def _valid_email(e):
    import re

    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e or ""))


def _support_ack_html(ticket_id, subject, message):
    return (
        f"<p>Thanks for reaching out to Personal AI. We've logged your "
        f"message and will get back to you soon.</p>"
        f"<p><b>Ticket:</b> #{ticket_id}<br><b>Subject:</b> "
        f"{subject or '(none)'}</p><hr>"
        f"<p style='white-space:pre-wrap;color:#555'>{message}</p>"
    )


def _support_notify_html(ticket_id, email, category, subject, message):
    return (
        f"<p>New support request <b>#{ticket_id}</b></p>"
        f"<p><b>From:</b> {email}<br><b>Category:</b> {category}<br>"
        f"<b>Subject:</b> {subject or '(none)'}</p><hr>"
        f"<p style='white-space:pre-wrap'>{message}</p>"
    )


@app.route("/api/support", methods=["POST"])
@limiter.limit("6 per hour;30 per day")
def submit_support():
    """Public contact/support endpoint (works logged-in or anonymous)."""
    data = request.get_json(silent=True) or {}
    uid = session.get("user_id")
    email = (data.get("email") or session.get("user_email") or "").strip()
    subject = (data.get("subject") or "").strip()[:300]
    category = (data.get("category") or "general").strip().lower()
    message = (data.get("message") or "").strip()
    if category not in SUPPORT_CATEGORIES:
        category = "general"
    if not _valid_email(email):
        return (
            jsonify({"error": "invalid_email", "detail": "A valid email is required."}),
            400,
        )
    if len(message) < 5:
        return (
            jsonify(
                {"error": "empty_message", "detail": "Please describe your issue."}
            ),
            400,
        )
    message = message[:5000]

    db = SessionLocal()
    try:
        sr = SupportRequest(
            user_id=uid,
            email=email,
            subject=subject,
            category=category,
            message=message,
        )
        db.add(sr)
        db.commit()
        ticket_id = sr.id
    finally:
        db.close()

    email_service.send(
        email,
        f"We received your message (#{ticket_id})",
        _support_ack_html(ticket_id, subject, message),
        reply_to=SUPPORT_EMAIL or None,
    )
    if SUPPORT_EMAIL:
        email_service.send(
            SUPPORT_EMAIL,
            f"[{category}] {subject or 'New support request'} (#{ticket_id})",
            _support_notify_html(ticket_id, email, category, subject, message),
            reply_to=email,
        )
    log_security_event("support_submitted", ticket=ticket_id, category=category)
    return jsonify({"ok": True, "ticket": ticket_id})


@app.route("/api/memories", methods=["GET"])
@login_required
def list_memories():
    db = SessionLocal()
    try:
        mems = (
            db.execute(
                select(Memory)
                .where(Memory.user_id == session["user_id"])
                .order_by(Memory.created_at.desc())
            )
            .scalars()
            .all()
        )
        return jsonify(
            [
                {
                    "id": m.id,
                    "fact": m.fact,
                    "project_id": m.project_id,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat(),
                }
                for m in mems
            ]
        )
    finally:
        db.close()


@app.route("/api/memories/<int:mid>", methods=["PATCH"])
@login_required
def update_memory(mid):
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        m = db.get(Memory, mid)
        if not m or m.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        if "fact" in data:
            m.fact = str(data["fact"])[:1000]
        if "importance" in data:
            m.importance = max(1, min(5, int(data["importance"])))
        db.commit()
        return jsonify(
            {
                "id": m.id,
                "fact": m.fact,
                "project_id": m.project_id,
                "importance": m.importance,
                "created_at": m.created_at.isoformat(),
            }
        )
    finally:
        db.close()


@app.route("/api/memories/<int:mid>", methods=["DELETE"])
@login_required
def delete_memory(mid):
    db = SessionLocal()
    try:
        m = db.get(Memory, mid)
        if not m or m.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        db.delete(m)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


def sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def image_data_url(path, mime):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime or 'image/png'};base64,{b64}"


def run_tool(name, args, user_id, project_id):
    if name == "web_search":
        results = web_search(args.get("query", ""))
        return json.dumps(results, ensure_ascii=False), results
    if name == "save_citation":
        db = SessionLocal()
        try:
            c = Citation(
                user_id=user_id,
                project_id=project_id,
                authors=str(args.get("authors", ""))[:500],
                title=str(args.get("title", ""))[:500],
                year=str(args.get("year", ""))[:10],
                venue=str(args.get("venue", ""))[:300],
                doi=str(args.get("doi", ""))[:200],
                url=str(args.get("url", ""))[:600],
            )
            db.add(c)
            db.commit()
            return json.dumps({"saved": True, "id": c.id}), []
        finally:
            db.close()
    return json.dumps({"error": f"unknown tool {name}"}), []


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    cid = data.get("conversation_id")
    user_message = (data.get("message") or "").strip()
    attachment_ids = data.get("attachments") or []
    regenerate = bool(data.get("regenerate"))
    search_mode = data.get("search", "auto")
    user_id = session["user_id"]

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        convo = db.get(Conversation, cid) if cid else None
        if not convo or convo.user_id != user_id:
            return jsonify({"error": "conversation_not_found"}), 404
        model = data.get("model") if data.get("model") in get_models() else convo.model
        project = db.get(Project, convo.project_id) if convo.project_id else None

        atts = []
        for fid in attachment_ids[:8]:
            x = db.get(UserFile, fid)
            if x and x.user_id == user_id:
                x.conversation_id = convo.id
                if convo.project_id and not x.project_id:
                    x.project_id = convo.project_id
                atts.append(
                    {
                        "id": x.id,
                        "name": x.name,
                        "mime": x.mime,
                        "kind": x.kind,
                        "path": x.path,
                        "text_len": x.text_len,
                    }
                )

        if regenerate:
            msgs = list(convo.messages)
            if msgs and msgs[-1].role == "assistant":
                db.delete(msgs[-1])
                db.commit()
        else:
            if not user_message and not atts:
                return jsonify({"error": "empty_message"}), 400
            db.add(
                Message(
                    conversation_id=convo.id,
                    role="user",
                    content=user_message or "(see attached files)",
                    attachments=(
                        json.dumps(
                            [
                                {k: a[k] for k in ("id", "name", "mime", "kind")}
                                for a in atts
                            ]
                        )
                        if atts
                        else None
                    ),
                )
            )
            convo.model = model
            db.commit()

        raw_msgs = db.get(Conversation, convo.id).messages
        history = []
        for m in raw_msgs:
            content = m.content
            m_atts = json.loads(m.attachments) if m.attachments else []
            if m_atts:
                names = ", ".join(a["name"] for a in m_atts)
                content = f"[attached files: {names}]\n{content}"
            history.append({"role": m.role, "content": content})
        memory_enabled = (
            bool(convo.memory_enabled) if convo.memory_enabled is not None else True
        )
        temperature = convo.temperature
        reasoning_effort = convo.reasoning_effort
        paper_file_id = convo.file_id  # M7: paper chat scope (may be None)

        # M7: if this is a paper chat, use a focused system prompt and
        # hard-scope retrieval to the single paper.
        if paper_file_id:
            paper = db.get(UserFile, paper_file_id)
            if paper and paper.user_id == user_id:
                system_prompt = build_paper_chat_prompt(user, paper)
            else:
                paper_file_id = None  # safety: invalid file, fall back
                system_prompt = build_system_prompt(user, project, memory_enabled)
        else:
            system_prompt = build_system_prompt(user, project, memory_enabled)

        convo_id = convo.id
        needs_title = not convo.title_generated
        project_id = convo.project_id
    finally:
        db.close()

    def generate():
        input_items = list(history)
        sources = []
        full_text = ""
        try:
            last_query = user_message or (history[-1]["content"] if history else "")

            doc_atts = [a for a in atts if a["kind"] == "document"]
            img_atts = [a for a in atts if a["kind"] == "image"]

            # The user turn we're answering — multimodal images attach here.
            user_idx = max(
                (i for i, m in enumerate(input_items) if m["role"] == "user"),
                default=None,
            )

            # M7: paper chat hard-scopes RAG to the single paper file
            excerpts = rag_retrieve(
                user_id, convo_id, project_id, last_query[:500], file_id=paper_file_id
            )
            if excerpts:
                yield sse("status", {"text": "Reading your documents…"})
                input_items.append(
                    {
                        "role": "developer",
                        "content": (
                            "Relevant excerpts from the user's uploaded documents.\n"
                            "Each excerpt may include 'page' (1-based PDF page) and/or "
                            "'section' (heading the excerpt falls under). "
                            "When citing, be specific: prefer 'p. 4, §Methodology' over "
                            "just the filename. If no locator is present, cite by filename.\n"
                            + json.dumps(excerpts, ensure_ascii=False)
                        ),
                    }
                )

            # Deliver each attached document's content to the model. Small docs
            # go in whole; large ones get a generous head (RAG excerpts above
            # cover the rest); scanned PDFs are rasterised for the vision model;
            # unparseable files get an explicit, honest note (never silent).
            INLINE_DOC_CHARS = 30000
            vision_urls = []
            for a in doc_atts:
                with storage.local_copy(a["path"]) as local_path:
                    txt = extract_text(local_path, a["mime"], a["name"])
                    has_text = bool(txt) and not (
                        txt.startswith("[") and txt.endswith("]") and len(txt) < 400
                    )
                    if has_text:
                        body = (
                            txt
                            if len(txt) <= INLINE_DOC_CHARS
                            else (
                                txt[:INLINE_DOC_CHARS]
                                + f"\n\n[…truncated {len(txt) - INLINE_DOC_CHARS} more "
                                "characters; see the excerpts above for the rest.]"
                            )
                        )
                        input_items.append(
                            {
                                "role": "developer",
                                "content": f"Full text of attached file "
                                f"'{a['name']}':\n{body}",
                            }
                        )
                        continue
                    is_pdf = a["name"].lower().endswith(".pdf") or "pdf" in (
                        a["mime"] or ""
                    )
                    pages = []
                    if is_pdf:
                        try:
                            pages = pdf_page_images(local_path)
                        except Exception:
                            pages = []
                if pages:
                    vision_urls.extend(pages)
                    input_items.append(
                        {
                            "role": "developer",
                            "content": f"The attached PDF '{a['name']}' has no text "
                            f"layer (scanned). Its first {len(pages)} "
                            "page image(s) are attached to the user's "
                            "message — read them to answer.",
                        }
                    )
                else:
                    reason = (
                        txt.strip("[]")
                        if txt
                        else "no readable text could be extracted (it may be "
                        "empty, encrypted, or an unsupported binary "
                        "format)"
                    )
                    input_items.append(
                        {
                            "role": "developer",
                            "content": f"The attached file '{a['name']}' could not "
                            f"be parsed: {reason}. Do not fabricate its "
                            "contents — tell the user what happened and "
                            "suggest a fix (re-export as PDF/DOCX/XLSX or "
                            "paste the text).",
                        }
                    )

            for a in img_atts:
                try:
                    with storage.local_copy(a["path"]) as local_path:
                        vision_urls.append(image_data_url(local_path, a["mime"]))
                except Exception:
                    pass

            if vision_urls and user_idx is not None and not regenerate:
                base = input_items[user_idx]
                text_part = base["content"] if isinstance(base["content"], str) else ""
                content = [{"type": "input_text", "text": text_part}]
                for url in vision_urls[:16]:
                    content.append({"type": "input_image", "image_url": url})
                input_items[user_idx] = {"role": "user", "content": content}

            if search_mode == "on":
                yield sse("status", {"text": "Searching the web…"})
                results = web_search(last_query[:300])
                sources.extend(results)
                input_items.append(
                    {
                        "role": "developer",
                        "content": "Web search results (cite these):\n"
                        + json.dumps(results, ensure_ascii=False),
                    }
                )

            # Paper chat: disable all external search so the AI cannot pull
            # content from outside the uploaded document.
            if paper_file_id:
                tools = [TOOL_SAVE_CITATION]
            else:
                tools = [TOOL_SAVE_CITATION]
                if search_mode == "auto":
                    tools.append(TOOL_WEB_SEARCH)

            for _round in range(4):
                kwargs = dict(
                    model=model,
                    instructions=system_prompt,
                    input=input_items,
                    stream=True,
                    store=False,
                    tools=tools,
                )
                if temperature is not None and supports_temperature(model):
                    kwargs["temperature"] = temperature
                if reasoning_effort and supports_reasoning_effort(model):
                    kwargs["reasoning"] = {"effort": reasoning_effort}
                stream = client.responses.create(**kwargs)

                final = None
                for event in stream:
                    et = getattr(event, "type", "")
                    if et == "response.output_text.delta":
                        full_text += event.delta
                        yield sse("delta", {"text": event.delta})
                    elif et == "response.completed":
                        final = event.response
                    elif et == "response.failed":
                        raise RuntimeError(
                            getattr(
                                getattr(event.response, "error", None),
                                "message",
                                "response failed",
                            )
                        )

                _log_chat_cost(user_id, model, getattr(final, "usage", None))

                calls = [
                    it
                    for it in (final.output if final else [])
                    if getattr(it, "type", "") == "function_call"
                ]
                if calls:
                    for c in calls:
                        input_items.append(
                            {
                                "type": "function_call",
                                "call_id": c.call_id,
                                "name": c.name,
                                "arguments": c.arguments,
                            }
                        )
                        try:
                            args = json.loads(c.arguments)
                        except Exception:
                            args = {}
                        label = (
                            "Searching: " + args.get("query", "") + "…"
                            if c.name == "web_search"
                            else "Saving citation…"
                        )
                        yield sse("status", {"text": label})
                        output, src = run_tool(c.name, args, user_id, project_id)
                        sources.extend(src)
                        input_items.append(
                            {
                                "type": "function_call_output",
                                "call_id": c.call_id,
                                "output": output,
                            }
                        )
                    continue
                break

            new_title = None
            dbi = SessionLocal()
            try:
                dbi.add(
                    Message(
                        conversation_id=convo_id,
                        role="assistant",
                        content=full_text,
                        sources=json.dumps(sources) if sources else None,
                    )
                )
                c2 = dbi.get(Conversation, convo_id)
                c2.updated_at = datetime.now(timezone.utc)
                if needs_title and full_text:
                    new_title = generate_title(last_query, full_text)
                    if new_title:
                        c2.title = new_title
                        c2.title_generated = 1
                dbi.commit()
            finally:
                dbi.close()

            done_payload = {"sources": sources}
            if new_title:
                done_payload["title"] = new_title
            yield sse("done", done_payload)

            if memory_enabled:
                snapshot = history + [{"role": "assistant", "content": full_text}]
                threading.Thread(
                    target=extract_memories,
                    args=(user_id, project_id, snapshot),
                    daemon=True,
                ).start()

        except Exception as e:
            msg = str(e)
            if "invalid_api_key" in msg or "Incorrect API key" in msg:
                msg = (
                    "Your OpenAI API key seems invalid — check OPENAI_API_KEY in .env."
                )
            elif "insufficient_quota" in msg:
                msg = "Your OpenAI account is out of credit."
            elif "does not exist" in msg or "model_not_found" in msg:
                msg = (
                    f"Model '{model}' isn't available — pick another from the dropdown."
                )
            elif "image" in msg.lower() and "support" in msg.lower():
                msg = (
                    f"Model '{model}' doesn't support images — "
                    "switch to a vision model like gpt-4o or gpt-5."
                )
            yield sse("error", {"text": msg})

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 14: Semantic Search
# ══════════════════════════════════════════════════════════════════════════


def _cosine(a: list, b: list) -> float:
    """Safe cosine similarity — returns 0.0 on zero-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _keyword_score(query: str, text: str) -> float:
    """Fallback scorer: fraction of query words found in text."""
    words = query.lower().split()
    if not words:
        return 0.0
    t = text.lower()
    return sum(1 for w in words if w in t) / len(words)


@app.route("/api/search", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def semantic_search():
    """Unified semantic search across papers, notes, citations, and chats.

    Body:
      q           str         – search query (required, 2-500 chars)
      kinds       list[str]   – ["paper","note","citation","chat"] (default: all)
      project_id  int|null    – scope to a project (null = global)
      limit       int         – max results (default 20, max 50)

    Algorithm:
      1. Embed the query with text-embedding-3-small.
      2. For each kind:
           paper    → scan Chunk rows, cosine vs chunk embedding
           note     → scan Note rows, keyword score (no embeddings stored yet)
           citation → scan Citation rows, keyword score
           chat     → scan Message rows (assistant only), keyword score
      3. Merge, sort by score desc, return top `limit`.

    Each result:
      kind        "paper"|"note"|"citation"|"chat"
      ref_id      id in the source table
      title       display title
      snippet     up to 300 chars of matching text
      score       float 0-1
      url         frontend navigation URL
      page        int|null   (paper chunks only)
      section     str|null   (paper chunks only)
      file_name   str|null   (paper chunks only)
    """
    data = request.get_json(silent=True) or {}
    uid = session["user_id"]
    q = str(data.get("q") or "").strip()
    kinds = data.get("kinds") or ["paper", "note", "citation", "chat"]
    project_id = data.get("project_id")
    try:
        limit = max(1, min(50, int(data.get("limit", 20))))
    except (TypeError, ValueError):
        limit = 20

    if len(q) < 2:
        return (
            jsonify(
                {
                    "error": "query_too_short",
                    "detail": "Query must be at least 2 characters.",
                }
            ),
            400,
        )

    # Try to embed the query; fall back to keyword-only if embedding fails
    query_emb = None
    try:
        query_emb = embed_texts([q])[0]
    except Exception:
        pass

    results = []
    db = SessionLocal()
    try:
        # ── Papers (via Chunk rows) ──────────────────────────────────────────
        if "paper" in kinds:
            # Collect file ids visible to this user (optionally scoped to project)
            file_stmt = select(UserFile).where(
                UserFile.user_id == uid,
                UserFile.kind == "document",
            )
            if project_id is not None:
                file_stmt = file_stmt.where(UserFile.project_id == project_id)
            files = db.execute(file_stmt).scalars().all()
            file_ids = [f.id for f in files]
            file_map = {f.id: f for f in files}

            if file_ids:
                chunks = (
                    db.execute(select(Chunk).where(Chunk.file_id.in_(file_ids)))
                    .scalars()
                    .all()
                )
                for ch in chunks:
                    if query_emb and ch.embedding:
                        try:
                            emb = json.loads(ch.embedding)
                            score = _cosine(query_emb, emb)
                        except Exception:
                            score = _keyword_score(q, ch.content)
                    else:
                        score = _keyword_score(q, ch.content)
                    if score < 0.15:
                        continue
                    uf = file_map.get(ch.file_id)
                    title = (uf.title or uf.name) if uf else "Paper"
                    results.append(
                        {
                            "kind": "paper",
                            "ref_id": ch.file_id,
                            "chunk_id": ch.id,
                            "title": title,
                            "snippet": ch.content[:300],
                            "score": round(score, 4),
                            "url": f"/papers/{ch.file_id}",
                            "page": ch.page,
                            "section": ch.section,
                            "file_name": uf.name if uf else None,
                        }
                    )

        # ── Notes ───────────────────────────────────────────────────────────
        if "note" in kinds:
            note_stmt = select(Note).where(Note.user_id == uid)
            if project_id is not None:
                note_stmt = note_stmt.where(Note.project_id == project_id)
            notes = db.execute(note_stmt).scalars().all()
            for n in notes:
                text = (n.title or "") + " " + (n.content or "")
                score = _keyword_score(q, text)
                if score < 0.20:
                    continue
                results.append(
                    {
                        "kind": "note",
                        "ref_id": n.id,
                        "title": n.title or "Untitled note",
                        "snippet": (n.content or "")[:300],
                        "score": round(score, 4),
                        "url": "/notes",
                        "page": None,
                        "section": None,
                        "file_name": None,
                    }
                )

        # ── Citations ────────────────────────────────────────────────────────
        if "citation" in kinds:
            cit_stmt = select(Citation).where(Citation.user_id == uid)
            if project_id is not None:
                cit_stmt = cit_stmt.where(Citation.project_id == project_id)
            cits = db.execute(cit_stmt).scalars().all()
            for c in cits:
                text = " ".join(filter(None, [c.title, c.authors, c.venue, c.notes]))
                score = _keyword_score(q, text)
                if score < 0.20:
                    continue
                results.append(
                    {
                        "kind": "citation",
                        "ref_id": c.id,
                        "title": c.title or "Untitled",
                        "snippet": f"{c.authors} ({c.year}) — {c.venue}".strip(" —"),
                        "score": round(score, 4),
                        "url": "/citations",
                        "page": None,
                        "section": None,
                        "file_name": None,
                    }
                )

        # ── Chat messages ────────────────────────────────────────────────────
        if "chat" in kinds:
            msg_stmt = (
                select(Message, Conversation)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(
                    Conversation.user_id == uid,
                    Message.role == "assistant",
                )
            )
            if project_id is not None:
                msg_stmt = msg_stmt.where(Conversation.project_id == project_id)
            rows = db.execute(msg_stmt.limit(2000)).all()
            seen_convos: set[int] = set()  # max 1 result per conversation
            for msg, convo in rows:
                if convo.id in seen_convos:
                    continue
                score = _keyword_score(q, msg.content or "")
                if score < 0.25:
                    continue
                seen_convos.add(convo.id)
                results.append(
                    {
                        "kind": "chat",
                        "ref_id": convo.id,
                        "title": convo.title or "Untitled chat",
                        "snippet": (msg.content or "")[:300],
                        "score": round(score, 4),
                        "url": f"/c/{convo.id}",
                        "page": None,
                        "section": None,
                        "file_name": None,
                    }
                )

    finally:
        db.close()

    # Sort by score desc, then deduplicate paper results by file (keep best chunk)
    results.sort(key=lambda r: -r["score"])
    seen_papers: set[int] = set()
    deduped = []
    for r in results:
        if r["kind"] == "paper":
            if r["ref_id"] in seen_papers:
                continue
            seen_papers.add(r["ref_id"])
        deduped.append(r)

    return jsonify(
        {
            "q": q,
            "total": len(deduped),
            "results": deduped[:limit],
        }
    )


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 11: Multi-Paper Analysis (comparison)
# ══════════════════════════════════════════════════════════════════════════

_COMPARE_PROMPT = """You are an expert research analyst comparing multiple academic papers.

Given the structured analyses of {n} papers below, produce a JSON object with the following keys. Use null for any section that genuinely cannot be answered from the provided analyses. Never fabricate. Be specific.

Keys:
  overview         – 2-3 sentence description of what these papers share and how they differ
  similarities     – array of strings: themes, approaches, or findings common to ALL papers
  differences      – array of strings: key ways the papers diverge (method, scope, results)
  common_datasets  – array of dataset names used by 2 or more papers ([] if none)
  methodologies    – object {{paper_title: one-line methodology summary}} for each paper
  agreements       – array: claims or conclusions the papers agree on
  contradictions   – array: claims or findings that conflict across papers
  research_trends  – array: patterns or directions evident across the set
  synthesis        – 3-5 sentences: what does reading these papers together reveal?

Papers (as structured analyses):
{analyses}
"""

_COMPARE_MAX_ANALYSES_CHARS = 20_000  # generous but bounded


def _selection_hash(file_ids: list[int]) -> str:
    """Stable hash of a sorted file-id set."""
    key = ",".join(str(i) for i in sorted(set(file_ids)))
    return _hashlib.sha256(key.encode()).hexdigest()


def _derived_to_dict(da: DerivedAnalysis) -> dict:
    data = {}
    if da.data:
        try:
            data = json.loads(da.data)
        except Exception:
            pass
    return {
        "id": da.id,
        "kind": da.kind,
        "file_ids": json.loads(da.file_ids) if da.file_ids else [],
        "status": "done" if data else "pending",
        "data": data,
        "model": da.model or "",
        "created_at": da.created_at.isoformat() if da.created_at else None,
    }


def _run_comparison(
    derived_id: int, analyses_payload: str, file_ids: list[int]
) -> None:
    """Background worker: call the model and store the comparison result."""
    db = SessionLocal()
    try:
        da = db.get(DerivedAnalysis, derived_id)
        if not da:
            return

        prompt = _COMPARE_PROMPT.format(
            n=len(file_ids),
            analyses=analyses_payload[:_COMPARE_MAX_ANALYSES_CHARS],
        )
        raw = responses_text(prompt, json_mode=True)
        data = json.loads(raw)

        # Normalise array fields
        for arr_key in (
            "similarities",
            "differences",
            "common_datasets",
            "agreements",
            "contradictions",
            "research_trends",
        ):
            v = data.get(arr_key)
            if not isinstance(v, list):
                data[arr_key] = [v] if v and isinstance(v, str) else []
        if not isinstance(data.get("methodologies"), dict):
            data["methodologies"] = {}

        da = db.get(DerivedAnalysis, derived_id)
        if not da:
            return
        da.data = json.dumps(data, ensure_ascii=False)
        da.model = UTILITY_MODEL
        db.commit()

    except Exception as exc:
        logging.getLogger(__name__).warning(
            "comparison failed for derived_id=%s: %s", derived_id, exc
        )
        try:
            da2 = db.get(DerivedAnalysis, derived_id)
            if da2:
                da2.data = json.dumps({"error": str(exc)})
                da2.model = ""
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@app.route("/api/analysis/compare", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def compare_papers():
    """Generate (or return cached) a multi-paper comparison.

    Body:
      file_ids    list[int]   – 2-10 document file IDs to compare
      project_id  int|null    – optional project scope (informational only)
      force       bool        – if true, ignore cached result and regenerate

    Flow:
      1. Validate ownership of every file_id.
      2. Compute selection_hash and check DerivedAnalysis cache.
      3. If cache hit and not force → return immediately.
      4. Collect PaperAnalysis.data for each file (must be status='done').
         Papers without a completed analysis are skipped with a warning.
      5. Fire background comparison; return {status:'running', id:<id>}.

    Polling: GET /api/analysis/compare/<id>
    """
    data = request.get_json(silent=True) or {}
    uid = session["user_id"]
    file_ids = [int(i) for i in (data.get("file_ids") or []) if i]
    project_id = data.get("project_id")
    force = bool(data.get("force"))

    if len(file_ids) < 2:
        return (
            jsonify(
                {"error": "too_few", "detail": "Select at least 2 papers to compare."}
            ),
            400,
        )
    if len(file_ids) > 10:
        return (
            jsonify(
                {"error": "too_many", "detail": "Maximum 10 papers per comparison."}
            ),
            400,
        )

    db = SessionLocal()
    try:
        # Validate ownership + collect ready analyses
        valid_ids = []
        skipped = []
        paper_blobs = {}  # file_id -> {title, analysis_data}

        for fid in file_ids:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != uid:
                skipped.append({"id": fid, "reason": "not_found"})
                continue
            pa = db.execute(
                select(PaperAnalysis).where(PaperAnalysis.file_id == fid)
            ).scalar_one_or_none()
            if not pa or pa.status != "done":
                skipped.append(
                    {
                        "id": fid,
                        "name": uf.title or uf.name,
                        "reason": "analysis_not_ready",
                    }
                )
                continue
            valid_ids.append(fid)
            paper_blobs[fid] = {
                "title": uf.title or uf.name,
                "authors": uf.authors or "",
                "year": uf.year or "",
                "analysis": json.loads(pa.data) if pa.data else {},
            }

        if len(valid_ids) < 2:
            return (
                jsonify(
                    {
                        "error": "too_few_ready",
                        "detail": "At least 2 papers need a completed analysis. "
                        "Try again after analysis finishes.",
                        "skipped": skipped,
                    }
                ),
                400,
            )

        sel_hash = _selection_hash(valid_ids)

        # Cache check
        existing = db.execute(
            select(DerivedAnalysis).where(
                DerivedAnalysis.user_id == uid,
                DerivedAnalysis.kind == "compare",
                DerivedAnalysis.selection_hash == sel_hash,
            )
        ).scalar_one_or_none()

        if existing and not force:
            result = _derived_to_dict(existing)
            result["skipped"] = skipped
            return jsonify(result)

        # Build analyses payload for the prompt
        blobs_text = json.dumps(
            [paper_blobs[fid] for fid in valid_ids], ensure_ascii=False, indent=1
        )

        # Create or reset the DerivedAnalysis row
        if existing:
            existing.data = ""
            existing.model = ""
            existing.file_ids = json.dumps(valid_ids)
            db.commit()
            da_id = existing.id
        else:
            da = DerivedAnalysis(
                user_id=uid,
                project_id=project_id,
                kind="compare",
                selection_hash=sel_hash,
                file_ids=json.dumps(valid_ids),
            )
            db.add(da)
            db.commit()
            da_id = da.id

        # Fire background comparison
        threading.Thread(
            target=_run_comparison,
            args=(da_id, blobs_text, valid_ids),
            daemon=True,
        ).start()

        return jsonify(
            {
                "id": da_id,
                "kind": "compare",
                "status": "running",
                "file_ids": valid_ids,
                "skipped": skipped,
                "data": {},
            }
        )
    finally:
        db.close()


@app.route("/api/analysis/compare/<int:da_id>", methods=["GET"])
@login_required
def get_comparison(da_id):
    """Poll for comparison results. Returns {status:'running'|'done', data:{...}}."""
    db = SessionLocal()
    try:
        da = db.get(DerivedAnalysis, da_id)
        if not da or da.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_derived_to_dict(da))
    finally:
        db.close()


@app.route("/api/analysis/compare/<int:da_id>", methods=["DELETE"])
@login_required
def delete_comparison(da_id):
    """Clear a cached comparison so the next POST will regenerate it."""
    db = SessionLocal()
    try:
        da = db.get(DerivedAnalysis, da_id)
        if not da or da.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        db.delete(da)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 12: Research Gap Finder
# ══════════════════════════════════════════════════════════════════════════

_GAP_PROMPT = """You are an expert research analyst identifying gaps, open questions, and opportunities across a set of academic papers.

Given the structured analyses of {n} papers, produce a JSON object with the keys below. Base every finding strictly on the provided content — never fabricate gaps, assumptions, or ideas. If you are uncertain, say so rather than inventing something.

IMPORTANT: Label all output explicitly as AI-generated suggestions, not factual claims. This is enforced in the output keys themselves.

Keys:
  preamble              – 1-2 sentences: what field / subfield these papers cover
  underexplored_topics  – array of strings: topics the papers acknowledge but do not thoroughly investigate
  missing_experiments   – array of strings: experiments that would strengthen claims but are absent from these papers
  open_questions        – array of strings: explicit research questions raised but not resolved across the set
  methodological_gaps   – array of strings: limitations in methods used that future work should address
  dataset_gaps          – array of strings: missing data, domains, or populations not studied
  potential_thesis_ideas– array of strings: concrete thesis/dissertation topics a researcher could pursue based on these gaps
  future_opportunities  – array of strings: promising research directions emerging from the combined findings
  disclaimer            – MUST equal exactly: "These are AI-generated suggestions based on the provided paper analyses. They should be treated as starting points for your own critical assessment, not as definitive research conclusions."

Papers (as structured analyses):
{analyses}
"""

_GAP_MAX_ANALYSES_CHARS = 20_000


def _run_gap_finder(
    derived_id: int, analyses_payload: str, file_ids: list[int]
) -> None:
    """Background worker: call the model and store gap analysis result."""
    db = SessionLocal()
    try:
        da = db.get(DerivedAnalysis, derived_id)
        if not da:
            return

        prompt = _GAP_PROMPT.format(
            n=len(file_ids),
            analyses=analyses_payload[:_GAP_MAX_ANALYSES_CHARS],
        )
        raw = responses_text(prompt, json_mode=True)
        data = json.loads(raw)

        # Enforce the disclaimer regardless of what the model returned
        data["disclaimer"] = (
            "These are AI-generated suggestions based on the provided paper "
            "analyses. They should be treated as starting points for your own "
            "critical assessment, not as definitive research conclusions."
        )

        # Normalise all array fields
        for arr_key in (
            "underexplored_topics",
            "missing_experiments",
            "open_questions",
            "methodological_gaps",
            "dataset_gaps",
            "potential_thesis_ideas",
            "future_opportunities",
        ):
            v = data.get(arr_key)
            if not isinstance(v, list):
                data[arr_key] = [v] if v and isinstance(v, str) else []

        da = db.get(DerivedAnalysis, derived_id)
        if not da:
            return
        da.data = json.dumps(data, ensure_ascii=False)
        da.model = UTILITY_MODEL
        db.commit()

    except Exception as exc:
        logging.getLogger(__name__).warning(
            "gap finder failed for derived_id=%s: %s", derived_id, exc
        )
        try:
            da2 = db.get(DerivedAnalysis, derived_id)
            if da2:
                da2.data = json.dumps({"error": str(exc)})
                da2.model = ""
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@app.route("/api/analysis/gaps", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def find_gaps():
    """Identify research gaps across a set of papers (cached by selection).

    Body:
      file_ids    list[int]   – 2-10 document file IDs (must have completed analyses)
      project_id  int|null    – optional context (stored but not used in retrieval)
      force       bool        – if true, ignore cached result and regenerate

    Identical caching semantics to /api/analysis/compare:
      - selection_hash keyed on sorted file IDs
      - kind = 'gaps' (separate cache from comparison)
      - background thread; poll GET /api/analysis/gaps/<id>
    """
    data = request.get_json(silent=True) or {}
    uid = session["user_id"]
    file_ids = [int(i) for i in (data.get("file_ids") or []) if i]
    project_id = data.get("project_id")
    force = bool(data.get("force"))

    if len(file_ids) < 2:
        return jsonify({"error": "too_few", "detail": "Select at least 2 papers."}), 400
    if len(file_ids) > 10:
        return (
            jsonify(
                {"error": "too_many", "detail": "Maximum 10 papers per gap analysis."}
            ),
            400,
        )

    db = SessionLocal()
    try:
        valid_ids = []
        skipped = []
        paper_blobs = {}

        for fid in file_ids:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != uid:
                skipped.append({"id": fid, "reason": "not_found"})
                continue
            pa = db.execute(
                select(PaperAnalysis).where(PaperAnalysis.file_id == fid)
            ).scalar_one_or_none()
            if not pa or pa.status != "done":
                skipped.append(
                    {
                        "id": fid,
                        "name": uf.title or uf.name,
                        "reason": "analysis_not_ready",
                    }
                )
                continue
            valid_ids.append(fid)
            paper_blobs[fid] = {
                "title": uf.title or uf.name,
                "authors": uf.authors or "",
                "year": uf.year or "",
                "analysis": json.loads(pa.data) if pa.data else {},
            }

        if len(valid_ids) < 2:
            return (
                jsonify(
                    {
                        "error": "too_few_ready",
                        "detail": "At least 2 papers need a completed analysis.",
                        "skipped": skipped,
                    }
                ),
                400,
            )

        sel_hash = _selection_hash(valid_ids)  # same helper as M11

        existing = db.execute(
            select(DerivedAnalysis).where(
                DerivedAnalysis.user_id == uid,
                DerivedAnalysis.kind == "gaps",
                DerivedAnalysis.selection_hash == sel_hash,
            )
        ).scalar_one_or_none()

        if existing and not force:
            result = _derived_to_dict(existing)
            result["skipped"] = skipped
            return jsonify(result)

        blobs_text = json.dumps(
            [paper_blobs[fid] for fid in valid_ids], ensure_ascii=False, indent=1
        )

        if existing:
            existing.data = ""
            existing.model = ""
            existing.file_ids = json.dumps(valid_ids)
            db.commit()
            da_id = existing.id
        else:
            da = DerivedAnalysis(
                user_id=uid,
                project_id=project_id,
                kind="gaps",
                selection_hash=sel_hash,
                file_ids=json.dumps(valid_ids),
            )
            db.add(da)
            db.commit()
            da_id = da.id

        threading.Thread(
            target=_run_gap_finder,
            args=(da_id, blobs_text, valid_ids),
            daemon=True,
        ).start()

        return jsonify(
            {
                "id": da_id,
                "kind": "gaps",
                "status": "running",
                "file_ids": valid_ids,
                "skipped": skipped,
                "data": {},
            }
        )
    finally:
        db.close()


@app.route("/api/analysis/gaps/<int:da_id>", methods=["GET"])
@login_required
def get_gaps(da_id):
    """Poll for gap analysis results."""
    db = SessionLocal()
    try:
        da = db.get(DerivedAnalysis, da_id)
        if not da or da.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_derived_to_dict(da))
    finally:
        db.close()


@app.route("/api/analysis/gaps/<int:da_id>", methods=["DELETE"])
@login_required
def delete_gaps(da_id):
    """Clear a cached gap analysis."""
    db = SessionLocal()
    try:
        da = db.get(DerivedAnalysis, da_id)
        if not da or da.user_id != session["user_id"]:
            return jsonify({"error": "not_found"}), 404
        db.delete(da)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# RESEARCH WORKSPACE — Milestone 15: AI Writing Assistant + Export Center
# ══════════════════════════════════════════════════════════════════════════

WRITING_ACTIONS = {
    "rewrite_academic": (
        "Rewrite the following text in a formal, academic style suitable for "
        "a research paper. Preserve all facts and meaning. "
        "Do not add citations or data that is not already present."
    ),
    "improve_grammar": (
        "Correct all grammar, punctuation, and spelling errors in the text below. "
        "Do not change the meaning or add new content."
    ),
    "improve_clarity": (
        "Rewrite the following text to improve clarity and readability while "
        "keeping the same meaning and academic register."
    ),
    "expand": (
        "Expand the following paragraph with additional explanation and detail. "
        "Stay strictly within what the original text implies — do not invent "
        "facts, citations, or experiments."
    ),
    "shorten": (
        "Shorten the following text, removing redundancy and filler while "
        "preserving the key information."
    ),
    "generate_abstract": (
        "Write a concise academic abstract (150-250 words) for the text below. "
        "Structure: background, objective, method, results, conclusion. "
        "Do not invent data or claims not present in the text."
    ),
    "improve_conclusion": (
        "Rewrite the following conclusion to be stronger, clearer, and more "
        "impactful. Do not add claims not supported by the preceding text."
    ),
}


@app.route("/api/writing", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
def writing_assistant():
    """AI Writing Assistant — apply a research-focused transformation to text.

    Body:
      action  str  – one of the WRITING_ACTIONS keys
      text    str  – the text to transform (max 8 000 chars)

    Returns:
      result  str  – the transformed text
      action  str  – echoed back for reference
      warning str  – non-empty if the assistant had to hedge (e.g. too long)
    """
    data = request.get_json(silent=True) or {}
    action = str(data.get("action") or "").strip()
    text = str(data.get("text") or "").strip()

    if action not in WRITING_ACTIONS:
        return (
            jsonify(
                {
                    "error": "invalid_action",
                    "detail": f"Action must be one of: {', '.join(WRITING_ACTIONS)}",
                }
            ),
            400,
        )

    if not text:
        return (
            jsonify({"error": "text_required", "detail": "text field is required."}),
            400,
        )

    MAX_CHARS = 8_000
    warning = ""
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        warning = (
            "Input was truncated to 8 000 characters. "
            "For longer texts, split into sections."
        )

    instruction = WRITING_ACTIONS[action]
    prompt = (
        instruction
        + "\n\nIMPORTANT: If you are uncertain or lack context to make a requested "
        "change accurately, say so explicitly rather than inventing content.\n\n"
        + "Text:\n"
        + text
    )

    result = responses_text(prompt)

    return jsonify(
        {
            "result": result,
            "action": action,
            "warning": warning,
        }
    )


# ── Export Centre ─────────────────────────────────────────────────────────────


def _export_as_markdown(content_str: str, title: str = "") -> bytes:
    header = f"# {title}\n\n" if title else ""
    return (header + content_str).encode("utf-8")


def _export_as_docx(content_str: str, title: str = "") -> bytes:
    """Create a minimal DOCX from plain text.  Requires python-docx."""
    try:
        import docx as _docx
        from io import BytesIO

        doc = _docx.Document()
        if title:
            doc.add_heading(title, 0)
        for para in content_str.split("\n\n"):
            if para.strip():
                doc.add_paragraph(para.strip())
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
    except ImportError:
        # Fall back to plain text if python-docx unavailable
        return content_str.encode("utf-8")


@app.route("/api/export/notes", methods=["POST"])
@login_required
def export_notes():
    """Export user notes as Markdown, plain text, or DOCX.

    Body:
      format      str       – "md" | "txt" | "docx" (default "md")
      project_id  int|null  – scope to a project
      note_ids    list[int] – export specific notes (null = all)
    """
    data = request.get_json(silent=True) or {}
    uid = session["user_id"]
    fmt = str(data.get("format") or "md").lower()
    project_id = data.get("project_id")
    note_ids = data.get("note_ids")  # list[int] or null

    db = SessionLocal()
    try:
        stmt = select(Note).where(Note.user_id == uid)
        if project_id is not None:
            stmt = stmt.where(Note.project_id == project_id)
        if note_ids:
            stmt = stmt.where(Note.id.in_([int(i) for i in note_ids]))
        notes = db.execute(stmt.order_by(Note.updated_at.desc())).scalars().all()
    finally:
        db.close()

    sections = []
    for n in notes:
        if n.title:
            sections.append(f"## {n.title}\n\n{n.content or ''}")
        else:
            sections.append(n.content or "")
    body = "\n\n---\n\n".join(sections)

    if fmt == "docx":
        blob = _export_as_docx(body, "Research Notes")
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        fname = "notes.docx"
    elif fmt == "txt":
        blob = body.encode("utf-8")
        mime = "text/plain"
        fname = "notes.txt"
    else:
        blob = _export_as_markdown(body, "Research Notes")
        mime = "text/markdown"
        fname = "notes.md"

    return send_file(
        io.BytesIO(blob), mimetype=mime, as_attachment=True, download_name=fname
    )


@app.route("/api/export/analysis/<int:file_id>", methods=["GET"])
@login_required
def export_analysis(file_id):
    """Export the 14-field paper analysis for one file.

    Query params:
      format  str  – "md" | "txt" | "docx" (default "md")
    """
    uid = session["user_id"]
    fmt = request.args.get("format", "md").lower()

    db = SessionLocal()
    try:
        uf = db.get(UserFile, file_id)
        if not uf or uf.user_id != uid:
            return jsonify({"error": "not_found"}), 404

        pa = db.execute(
            select(PaperAnalysis).where(PaperAnalysis.file_id == file_id)
        ).scalar_one_or_none()

        if not pa or pa.status != "done":
            return (
                jsonify(
                    {
                        "error": "analysis_not_ready",
                        "detail": "Analysis not yet complete.",
                    }
                ),
                400,
            )

        analysis = json.loads(pa.data) if pa.data else {}
    finally:
        db.close()

    title = uf.title or uf.name
    lines = [f"# Paper Analysis: {title}", ""]
    field_labels = {
        "executive_summary": "Executive Summary",
        "abstract_explained": "Abstract Explained",
        "research_objective": "Research Objective",
        "problem_statement": "Problem Statement",
        "methodology": "Methodology",
        "dataset": "Dataset",
        "experiments": "Experiments",
        "results": "Results",
        "key_contributions": "Key Contributions",
        "strengths": "Strengths",
        "limitations": "Limitations",
        "future_work": "Future Work",
        "keywords": "Keywords",
        "important_terms": "Important Terms",
    }
    for key, label in field_labels.items():
        val = analysis.get(key)
        if not val:
            continue
        lines.append(f"## {label}")
        if isinstance(val, list):
            for item in val:
                lines.append(f"- {item}")
        elif isinstance(val, dict):
            for term, defn in val.items():
                lines.append(f"**{term}**: {defn}")
        else:
            lines.append(str(val))
        lines.append("")

    body = "\n".join(lines)

    if fmt == "docx":
        blob = _export_as_docx(body, f"Analysis: {title}")
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        fname = f"analysis-{file_id}.docx"
    elif fmt == "txt":
        blob = body.encode("utf-8")
        mime = "text/plain"
        fname = f"analysis-{file_id}.txt"
    else:
        blob = body.encode("utf-8")
        mime = "text/markdown"
        fname = f"analysis-{file_id}.md"

    return send_file(
        io.BytesIO(blob), mimetype=mime, as_attachment=True, download_name=fname
    )


@app.route("/api/export/chat/<int:cid>", methods=["GET"])
@login_required
def export_chat(cid):
    """Export a full conversation as Markdown or plain text.

    Query params:
      format  str  – "md" | "txt" (default "md")
    """
    uid = session["user_id"]
    fmt = request.args.get("format", "md").lower()

    db = SessionLocal()
    try:
        convo = db.execute(
            select(Conversation).where(
                Conversation.id == cid,
                Conversation.user_id == uid,
            )
        ).scalar_one_or_none()
        if not convo:
            return jsonify({"error": "not_found"}), 404
        messages = list(convo.messages)
    finally:
        db.close()

    lines = [f"# {convo.title or 'Conversation'}", ""]
    for m in messages:
        role = "**You**" if m.role == "user" else "**Assistant**"
        lines.append(f"{role}\n\n{m.content or ''}")
        lines.append("\n---\n")

    body = "\n".join(lines)

    if fmt == "txt":
        blob = body.encode("utf-8")
        mime = "text/plain"
        fname = f"chat-{cid}.txt"
    else:
        blob = body.encode("utf-8")
        mime = "text/markdown"
        fname = f"chat-{cid}.md"

    return send_file(
        io.BytesIO(blob), mimetype=mime, as_attachment=True, download_name=fname
    )


# ------------------------------------------------------------------ SPA (React build) serving
FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "frontend", "dist"
)


@app.route("/assets/<path:filename>")
def spa_assets(filename):
    # Vite content-hashes asset filenames, so they can be cached forever.
    return send_from_directory(
        os.path.join(FRONTEND_DIST, "assets"), filename, max_age=31536000
    )


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    # Real API/auth/static routes are matched by their explicit rules first;
    # this catch-all only fires for unmatched paths (client-side routes). The
    # guard turns a stray /api/... typo into a 404 instead of the SPA shell.
    if path.startswith(("api/", "auth/", "static/", "assets/")) or path in (
        "login",
        "logout",
        "robots.txt",
    ):
        abort(404)
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_path):
        return ("Frontend build not found — run `npm run build` in frontend/.", 501)
    return send_from_directory(FRONTEND_DIST, "index.html")


if __name__ == "__main__":
    print("Personal AI running -> http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
