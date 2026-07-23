"""Tests for the AI-layer integration added to /api/chat's system-prompt
building and cost logging — see server.py's _get_chat_system_opening()
and _log_chat_cost().

No existing chat tests existed to "update" (grepped for any — none in
this project before this task) and the core model call in /api/chat
still goes through client.responses.create() directly, not
ModelRegistry (see the recorded reasoning: /api/chat's multi-round
tool-calling loop, live SSE streaming, and vision support have no
equivalent in ModelRegistry today — replacing the call itself would
mean dropping web search, citation-saving, and real-time streaming, or
building substantial new capability into model_registry.py first,
neither of which this task asked for). What's new and testable is the
prompt-registry-backed system-prompt opening and the cost-ledger
logging this task actually added — that's what these tests cover
instead of a "mock ModelRegistry" that wouldn't reflect what's real.

DATABASE_URL isolation (so this never touches the real local chat_dev.db)
lives in the project's root conftest.py, not here — see that file for
why per-file env-var assignment was fragile (it silently didn't work
when this file wasn't the first one pytest happened to collect).

Run: pytest test_chat.py -v
"""

import pytest
from dotenv import load_dotenv

load_dotenv(override=False)  # OPENAI_API_KEY etc. — never overrides conftest.py's DATABASE_URL

import server
from backend.ai import PromptRegistry
from backend.ai.model_registry import CostLedgerEntry
from backend.ai.prompt_registry import PromptVersion


@pytest.fixture
def db():
    session = server.SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clean_chat_system_prompt(db):
    """Every test starts from "not seeded" — matches the real state of
    a fresh DB backfill.py hasn't touched, and keeps tests independent
    of each other regardless of run order."""
    db.query(PromptVersion).filter_by(name="chat_system").delete()
    db.commit()
    yield
    db.query(PromptVersion).filter_by(name="chat_system").delete()
    db.commit()


# ------------------------------------------------------------ _get_chat_system_opening
def test_falls_back_when_chat_system_not_seeded(db):
    opening = server._get_chat_system_opening(db)
    assert opening == server._CHAT_SYSTEM_FALLBACK


def test_uses_registry_when_chat_system_seeded(db):
    registry = PromptRegistry(db)
    # status="active" required: PromptRegistry's own default is "draft"
    # (migration 0015's authoring lifecycle) — a draft has no active
    # version for _get_chat_system_opening()'s no-explicit-version lookup
    # to find, so without this the fallback would fire instead.
    registry.create_prompt("chat_system", "test", "Custom system prompt from the registry.", status="active")

    opening = server._get_chat_system_opening(db)

    assert opening == "Custom system prompt from the registry."


def test_falls_back_on_unexpected_registry_error(db, mocker):
    mocker.patch.object(server, "get_prompt_registry", side_effect=RuntimeError("db exploded"))

    opening = server._get_chat_system_opening(db)

    assert opening == server._CHAT_SYSTEM_FALLBACK


def test_build_system_prompt_still_includes_dynamic_parts(db):
    user = server.User(email="promptbuildtest@example.com", name="Ada Lovelace", auth_provider="dev")
    db.add(user)
    db.commit()

    prompt = server.build_system_prompt(user, project=None, memory_enabled=False)

    assert server._CHAT_SYSTEM_FALLBACK in prompt
    assert "Ada Lovelace" in prompt
    db.delete(user)
    db.commit()


# ------------------------------------------------------------ _log_chat_cost
class _FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


def test_log_chat_cost_writes_row(db):
    user = server.User(email="costlogtest@example.com", name="T", auth_provider="dev")
    db.add(user)
    db.commit()
    user_id = user.id

    server._log_chat_cost(user_id, "gpt-4o-mini", _FakeUsage(100, 50))

    rows = db.query(CostLedgerEntry).filter_by(user_id=user_id, action="chat").all()
    assert len(rows) == 1
    assert rows[0].model == "gpt-4o-mini"
    assert rows[0].prompt_tokens == 100
    assert rows[0].completion_tokens == 50
    assert rows[0].total_tokens == 150
    assert rows[0].cost > 0

    db.query(CostLedgerEntry).filter_by(user_id=user_id).delete()
    db.delete(user)
    db.commit()


def test_log_chat_cost_noop_when_usage_none(db):
    server._log_chat_cost(999999, "gpt-4o-mini", None)  # must not raise
    assert db.query(CostLedgerEntry).filter_by(user_id=999999).count() == 0


def test_log_chat_cost_is_best_effort_on_failure(mocker):
    mocker.patch.object(server, "get_cost_ledger", side_effect=RuntimeError("ledger unavailable"))
    server._log_chat_cost(1, "gpt-4o-mini", _FakeUsage(10, 5))  # must not raise


# ------------------------------------------------------------ preview_chat_prompt_builder_migration
def test_preview_chat_migration_returns_legacy_and_candidate_side_by_side(db):
    # Same "chat_system" name /api/chat's own _get_chat_system_opening
    # already uses — see docs/chat-migration-roadmap.md §3 on why this
    # is deliberately NOT SystemPromptManager's separate "system_prompt".
    # PromptBuilder.build() always resolves SystemPromptManager's own
    # "system_prompt" first regardless of task_name, so both need seeding
    # here — found by actually running this, not assumed: the first
    # version of this test only seeded "chat_system" and hit exactly the
    # ValueError this comment now explains.
    registry = server.PromptRegistry(db)
    registry.create_prompt("chat_system", "test", "Custom opening line.", status="active")
    registry.create_prompt("system_prompt", "test", "Global system text.", status="active")

    user = server.User(email="chatmigrationtest@example.com", name="Ada Lovelace", auth_provider="dev")
    db.add(user)
    db.commit()

    try:
        result = server.preview_chat_prompt_builder_migration(user, project=None, memory_enabled=False)

        assert "Custom opening line." in result["legacy_system_prompt"]
        assert "Ada Lovelace" in result["legacy_system_prompt"]
        assert result["prompt_builder_task"] == "Custom opening line."
        assert result["prompt_builder_system"] == "Global system text."
        assert "Ada Lovelace" in result["not_yet_covered_by_prompt_builder"]["user_identity_and_date"]
        # The candidate's own assembled text doesn't yet include user
        # identity/date — confirms the roadmap's §2 gap is real, not
        # just asserted in a comment.
        assert "Ada Lovelace" not in result["prompt_builder_final"]
    finally:
        db.delete(user)
        db.query(PromptVersion).filter_by(name="chat_system").delete()
        db.query(PromptVersion).filter_by(name="system_prompt").delete()
        db.commit()
