"""Prometheus metrics, shared between server.py and worker.py.

Each process gets its OWN copy of these Counter/Gauge objects and its own
/metrics-equivalent exposition endpoint (server.py: a Flask route reusing
its process's default registry; worker.py: prometheus_client's own tiny
HTTP server on a separate port, via start_worker_metrics_server()) —
prometheus_client's registry is per-process, it cannot merge state across
two independent Python processes. That's not a gap to work around:
Prometheus scrapes both targets and aggregates server-side (`sum by
(model) (ai_calls_total)`), which is the standard way to handle a metric
produced by more than one process of the same logical service.

Label cardinality is deliberately bounded:
  - route uses the Flask route RULE ("/api/files/<int:fid>"), never
    request.path — the resolved path has one distinct value per file id
    and would make the label set grow forever.
  - AI token/call metrics are labeled by model (a small, fixed set), not
    by user_id. Per-user token accounting already exists and belongs in
    AIUsageLedger/CostLedger (SQL, queryable, no cardinality limit) —
    Prometheus is for operational aggregates, not a second billing
    ledger. See CostLedger/AIUsageLedger for "tokens used by user X".
"""

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    start_http_server,
)

REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    ["method", "route", "status"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    registry=REGISTRY,
)

AI_CALLS_TOTAL = Counter(
    "ai_calls_total",
    "AI model calls, by logical model name",
    ["model"],
    registry=REGISTRY,
)

AI_TOKENS_TOTAL = Counter(
    "ai_tokens_total",
    "AI tokens consumed, by model and prompt/completion",
    ["model", "token_type"],
    registry=REGISTRY,
)

UPLOAD_QUEUE_LENGTH = Gauge(
    "upload_queue_length",
    "Current upload_jobs row count, by status",
    ["status"],
    registry=REGISTRY,
)


def record_ai_call(model: str, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    """Single call site for both AI metrics — every instrumented call
    site (ModelRegistry.call/embed, server.py's responses_text/
    embed_texts/_log_chat_cost) reports through this, so "what counts as
    an AI call" is defined once."""
    model = model or "unknown"
    AI_CALLS_TOTAL.labels(model=model).inc()
    if prompt_tokens:
        AI_TOKENS_TOTAL.labels(model=model, token_type="prompt").inc(prompt_tokens)
    if completion_tokens:
        AI_TOKENS_TOTAL.labels(model=model, token_type="completion").inc(completion_tokens)


def render_metrics() -> bytes:
    return generate_latest(REGISTRY)


def start_worker_metrics_server(port: int) -> None:
    """worker.py has no Flask app of its own to hang a /metrics route
    off of — prometheus_client's built-in HTTP server fills that gap.
    Uses the same REGISTRY as record_ai_call() above, so counters
    incremented in worker.py's job handlers actually show up here."""
    start_http_server(port, registry=REGISTRY)
