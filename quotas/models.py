"""UsageLog — a coarse, per-action audit trail of quota consumption
(upload/ai_query/export, amount in bytes or tokens depending on action).

Distinct from ai_usage_ledger (server.py): that table is a detailed,
AI-specific record (model, prompt/completion tokens, cost) written from
the two functions that actually call OpenAI. UsageLog is the generic
counterpart written by QuotaService itself, for any quota-consuming
action — including non-AI ones (storage) that ai_usage_ledger was never
meant to cover. Some overlap for the "ai_query" action specifically is
expected and fine: ai_usage_ledger has the detail, UsageLog has the
coarse total, the same relationship processing_metrics_daily has to
upload_jobs (database-design.md §2.3) — a summary layer coexisting with
a detailed one, not a duplicate of it.

Factory (create_usage_log_model), not a class importing `server` — same
reason as every other new module in this project's auth/ package: a
model needs server.py's actual Base (the specific declarative registry
"Base.metadata.create_all()" is called on), and server.py runs as
__main__, so importing "server" back from a module it reaches into would
re-execute the whole file under a second identity.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey


def create_usage_log_model(Base):
    class UsageLog(Base):
        __tablename__ = "usage_logs"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
        action = Column(String(30), nullable=False)  # upload | ai_query | export | ...
        amount = Column(
            Integer, default=0
        )  # bytes or tokens — meaning depends on action
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return UsageLog
