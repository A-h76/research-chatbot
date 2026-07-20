"""JSON structured logging + a correlation-id contextvar shared by
server.py (one HTTP request = one id) and worker.py (one job = one id).

Plain stdlib logging + a custom Formatter, not structlog: a JSON
formatter that reads record.__dict__ is a few lines and this app already
uses stdlib logging exclusively (server.py's security_log/email_log,
worker.py's own logger) — swapping the formatter is a much smaller,
lower-risk change than replacing the logging backend app-wide for what
the task's own instructions call an equally acceptable alternative
("structlog or JSON logs").

contextvars.ContextVar, not threading.local: correct under Flask's
threaded dev server (each request thread gets an isolated copy
automatically) without extra plumbing, and it's the same primitive
that'd be needed if either process ever went async.
"""
import contextvars
import json
import logging
from datetime import datetime, timezone

correlation_id_var: "contextvars.ContextVar[str | None]" = contextvars.ContextVar(
    "correlation_id", default=None
)

# Attributes logging.LogRecord always has — anything else on a record
# came from a caller's `logging.info(..., extra={...})` and should be
# surfaced as its own JSON field.
_STANDARD_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = correlation_id_var.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level=logging.INFO) -> None:
    """Call once per process, in place of logging.basicConfig(). force=True
    because both server.py and worker.py may already have a handler
    attached (e.g. re-imported under a test runner) — this replaces it
    rather than silently no-op'ing, which is basicConfig's default
    behavior once any handler exists."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
