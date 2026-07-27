"""CostLedger — cost estimation + persistence for ModelRegistry calls.

Keyed on raw provider model-name strings ("gpt-4o", "claude-3-5-sonnet"),
not server.py's internal model_versions.id — deliberately a separate,
narrower table from AIUsageLedger (server.py) and quotas.UsageLog, not a
rewrite of either. Neither fits here: AIUsageLedger requires resolving a
raw model string into a ModelVersion row first (no such resolver
exists), and UsageLog only records a coarse (action, amount) pair, not
per-provider token/cost detail. This overlap was a deliberate, discussed
tradeoff, not an oversight.

Factory (create_cost_ledger_model(Base)), same reason as every other new
model in this project: needs the caller's actual Base, and server.py
runs as __main__, so importing it back from a module it reaches into
would recurse. Does NOT create its table — assumes it already exists,
same as backend/ai/prompt_registry.py's PromptVersion.

Pricing table only covers models with confident, publicly documented
rates as of this writing. Anything absent returns cost=0.0 rather than a
fabricated number — a wrong-but-confident-looking dollar figure is worse
than an honest "unknown." gpt-5-family/o-series/gemini-2.0 models are
intentionally NOT in this table for that reason.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

logger = logging.getLogger(__name__)


def create_cost_ledger_model(Base):
    class CostLedgerEntry(Base):
        __tablename__ = "model_registry_cost_ledger"
        id = Column(Integer, primary_key=True)
        # No ForeignKey("users.id") here on purpose: the real users
        # table lives under server.py's own Base/metadata, a completely
        # separate declarative registry from this module's private one
        # (see model_registry.py's module docstring) — a FK across two
        # unrelated Base objects can't be resolved by
        # Base.metadata.create_all() at all, real table or not. A real
        # deployment would enforce this via a real migration against the
        # real users table, independent of this Python declaration.
        user_id = Column(Integer, nullable=True)
        model = Column(String(60), nullable=False)
        action = Column(String(30), nullable=False, default="chat")  # chat | embedding
        prompt_tokens = Column(Integer, default=0)
        completion_tokens = Column(Integer, default=0)
        total_tokens = Column(Integer, default=0)
        cost = Column(Float, default=0.0)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        # Closes the gap prompt-engine-audit.md §3 flagged: which prompt
        # version produced this call. Same cross-Base reasoning as
        # user_id above — prompt_versions lives under prompt_registry.py's
        # own private Base, a third registry — so this is a plain column,
        # migrations/0015 adds the real DB-level FK.
        prompt_version_id = Column(Integer, nullable=True)

    return CostLedgerEntry


class CostLedger:
    # $ per 1M tokens: (prompt_rate, completion_rate). Confident, public
    # pricing only — see module docstring.
    PRICING = {
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4-turbo": (10.00, 30.00),
        "gpt-4": (30.00, 60.00),
        "gpt-3.5-turbo": (0.50, 1.50),
        "claude-3-5-sonnet": (3.00, 15.00),
        "claude-3-5-haiku": (0.80, 4.00),
        "claude-3-opus": (15.00, 75.00),
        "claude-3-sonnet": (3.00, 15.00),
        "claude-3-haiku": (0.25, 1.25),
        "text-embedding-3-small": (0.02, 0.0),
    }

    def __init__(self, Model):
        self._Model = Model  # the mapped CostLedgerEntry class

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        # Exact match first, then prefix — real model ids often carry a
        # dated suffix ("claude-3-5-sonnet-20241022") the bare table key
        # won't exact-match, and prefix matching is a fair, obvious
        # extension for that case specifically. Falls back to (0.0, 0.0).
        rates = self.PRICING.get(model)
        if rates is None:
            rates = next((v for k, v in self.PRICING.items() if model.startswith(k)), None)
        if rates is None:
            logger.info("no known pricing for model %r, cost recorded as 0.0", model)
            rates = (0.0, 0.0)
        prompt_rate, completion_rate = rates
        return round(prompt_tokens / 1_000_000 * prompt_rate + completion_tokens / 1_000_000 * completion_rate, 6)

    def log(
        self,
        db_session,
        *,
        user_id,
        model,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        cost,
        action="chat",
        prompt_version_id=None,
    ):
        db_session.add(
            self._Model(
                user_id=user_id,
                model=model,
                action=action,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                prompt_version_id=prompt_version_id,
            )
        )
        db_session.commit()
