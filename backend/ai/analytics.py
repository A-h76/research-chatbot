"""PromptAnalytics — cost/usage aggregation across BOTH AI call paths
this app has: AIUsageLedger (server.py, the legacy OpenAI-Responses-API
path — /api/chat, the original worker.py job handlers) and
CostLedgerEntry (backend/ai/model_registry.py, the ModelRegistry path —
RAG, paper_analysis). See docs/prompt-engine-audit.md §3 for why these
are two separate tables in the first place, not a design flaw introduced
here.

__init__ takes AIUsageLedger/ModelVersion as constructor params, not
just db_session — those two are server.py's own real classes, and this
module can't `import server` to get them (server.py runs as __main__;
a module it reaches into importing it back re-executes the whole file
under a second module identity and recurses — same reason every other
module in backend/, auth/, quotas/ is constructor-injected). CostLedgerEntry/
PromptVersion/PromptExecution don't have that problem — they're real,
directly-importable classes from other backend/ai modules — so they're
plain module-level imports here, not injected.

Merges the two ledgers by fetching each separately and combining in
Python, not via a cross-Base SQL JOIN — a JOIN would need explicit
Table-level join conditions across three different declarative Bases,
which works but is genuinely more fragile to get and keep right than
"fetch both, merge in a dict" at the call volumes this app actually
has (a personal research tool, not a high-throughput SaaS — see
brain.md). Revisit if a real deployment's row counts ever make the
in-Python merge slow.

get_usage_by_project() is NOT built from the two ledgers — neither has
a project_id column at all. It's built entirely from PromptExecution
(migrations/0015_prompt_engine.sql), the only table that actually
associates an AI call with a project today; it has no cost_usd for the
same reason (PromptExecution only ever recorded token counts, not
dollar cost).
"""
from collections import defaultdict
from typing import List, Optional

from .model_registry import CostLedgerEntry
from .prompt_registry import PromptVersion, PromptExecution


def _empty_ledger_bucket():
    return {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}


def _accumulate(bucket, event):
    bucket["calls"] += 1
    bucket["prompt_tokens"] += event["prompt_tokens"]
    bucket["completion_tokens"] += event["completion_tokens"]
    bucket["total_tokens"] += event["total_tokens"]
    bucket["cost_usd"] += event["cost_usd"]


class PromptAnalytics:
    def __init__(self, db_session, AIUsageLedger, ModelVersion):
        self.db = db_session
        self.AIUsageLedger = AIUsageLedger
        self.ModelVersion = ModelVersion

    # ------------------------------------------------------------ unified events
    def _legacy_events(self, start_date, end_date) -> List[dict]:
        """AIUsageLedger rows. model_version_id is a FK to ModelVersion,
        not a raw model string like CostLedgerEntry.model — resolved via
        a join so both sources report `model` the same way.
        prompt_version_id exists on this table but nothing has ever
        populated it (prompt-engine-audit.md §3's dead-column finding) —
        those rows fall into the "unknown" bucket in get_usage_by_prompt,
        not dropped, so totals still reconcile."""
        rows = (
            self.db.query(self.AIUsageLedger, self.ModelVersion)
            .join(self.ModelVersion, self.AIUsageLedger.model_version_id == self.ModelVersion.id)
            .filter(self.AIUsageLedger.created_at >= start_date,
                   self.AIUsageLedger.created_at <= end_date)
            .all()
        )
        return [
            {
                "user_id": led.user_id,
                "model": mv.provider_model_id,
                "prompt_version_id": led.prompt_version_id,
                "prompt_tokens": led.prompt_tokens or 0,
                "completion_tokens": led.completion_tokens or 0,
                "total_tokens": (led.prompt_tokens or 0) + (led.completion_tokens or 0),
                "cost_usd": led.cost_usd or 0.0,
            }
            for led, mv in rows
        ]

    def _new_events(self, start_date, end_date) -> List[dict]:
        rows = (
            self.db.query(CostLedgerEntry)
            .filter(CostLedgerEntry.created_at >= start_date, CostLedgerEntry.created_at <= end_date)
            .all()
        )
        return [
            {
                "user_id": r.user_id,
                "model": r.model,
                "prompt_version_id": r.prompt_version_id,
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "total_tokens": r.total_tokens or 0,
                "cost_usd": r.cost or 0.0,
            }
            for r in rows
        ]

    def _unified_events(self, start_date, end_date) -> List[dict]:
        return self._legacy_events(start_date, end_date) + self._new_events(start_date, end_date)

    def _prompt_names(self) -> dict:
        return {p.id: p.name for p in self.db.query(PromptVersion).all()}

    # ------------------------------------------------------------ public
    def get_usage_by_model(self, start_date, end_date) -> List[dict]:
        buckets = defaultdict(_empty_ledger_bucket)
        for event in self._unified_events(start_date, end_date):
            _accumulate(buckets[event["model"]], event)
        return [{"model": key, **value} for key, value in sorted(buckets.items())]

    def get_usage_by_user(self, start_date, end_date) -> List[dict]:
        buckets = defaultdict(_empty_ledger_bucket)
        for event in self._unified_events(start_date, end_date):
            _accumulate(buckets[event["user_id"]], event)
        return [
            {"user_id": key, **value}
            for key, value in sorted(buckets.items(), key=lambda kv: (kv[0] is None, kv[0]))
        ]

    def get_usage_by_prompt(self, start_date, end_date) -> List[dict]:
        """Cost/tokens come from the unified ledgers; latency comes from
        PromptExecution — neither ledger tracks latency at all, so this
        is the one method that genuinely draws from both kinds of source
        in this file, joined by prompt name (via prompt_version_id ->
        PromptVersion.id, resolved once and reused for both halves)."""
        names = self._prompt_names()
        buckets = defaultdict(lambda: {**_empty_ledger_bucket(), "latency_ms_avg": None})

        for event in self._unified_events(start_date, end_date):
            key = names.get(event["prompt_version_id"], "unknown")
            _accumulate(buckets[key], event)

        latency_sums = defaultdict(lambda: [0, 0])   # name -> [sum, count]
        executions = (
            self.db.query(PromptExecution)
            .filter(PromptExecution.created_at >= start_date, PromptExecution.created_at <= end_date,
                   PromptExecution.latency_ms.isnot(None))
            .all()
        )
        for execution in executions:
            key = names.get(execution.prompt_version_id, "unknown")
            latency_sums[key][0] += execution.latency_ms
            latency_sums[key][1] += 1
        for key, (total, count) in latency_sums.items():
            if count:
                buckets[key]["latency_ms_avg"] = round(total / count, 1)

        return [{"prompt_name": key, **value} for key, value in sorted(buckets.items())]

    def get_usage_by_project(self, start_date, end_date) -> List[dict]:
        """PromptExecution only — see module docstring for why this
        can't be "unified" the way the other three methods are."""
        rows = (
            self.db.query(PromptExecution)
            .filter(PromptExecution.created_at >= start_date, PromptExecution.created_at <= end_date)
            .all()
        )
        buckets = defaultdict(lambda: {"calls": 0, "tokens_used": 0})
        latency_sums = defaultdict(lambda: [0, 0])
        for row in rows:
            bucket = buckets[row.project_id]
            bucket["calls"] += 1
            bucket["tokens_used"] += row.tokens_used or 0
            if row.latency_ms is not None:
                latency_sums[row.project_id][0] += row.latency_ms
                latency_sums[row.project_id][1] += 1

        result = []
        for key, value in sorted(buckets.items(), key=lambda kv: (kv[0] is None, kv[0])):
            total, count = latency_sums[key]
            result.append({
                "project_id": key, **value,
                "latency_ms_avg": round(total / count, 1) if count else None,
            })
        return result
