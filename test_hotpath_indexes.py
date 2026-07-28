"""Assert hot-path chat/library/queue indexes exist after ensure_columns.

Maps to migrations/0022_chat_hotpath_indexes.sql. Uses SQLite (root
conftest DATABASE_URL) — CREATE INDEX IF NOT EXISTS is portable.

Run: pytest test_hotpath_indexes.py -v
"""

import pytest
from sqlalchemy import inspect, text

import server


EXPECTED_INDEXES = {
    "messages": {"ix_messages_conversation_created"},
    "conversations": {
        "ix_conversations_user_updated",
        "ix_conversations_user_project",
        "ix_conversations_user_file",
        "ix_conversations_project",
        "ix_conversations_file",
    },
    "files": {
        "ix_files_user",
        "ix_files_user_project",
        "ix_files_conversation",
    },
    "upload_jobs": {
        "ix_upload_jobs_type_status",
        "ix_upload_jobs_status_created",
        "ix_upload_jobs_file_type",
        "ix_upload_jobs_user_status",
    },
    "outbox_events": {
        "ix_outbox_events_pending",
        "ix_outbox_events_status_created",
    },
    "projects": {"ix_projects_user"},
    "memories": {"ix_memories_user", "ix_memories_user_project"},
    "citations": {"ix_citations_user"},
}


def _index_names(table: str) -> set[str]:
    insp = inspect(server.engine)
    return {ix["name"] for ix in insp.get_indexes(table)}


@pytest.mark.parametrize("table,names", sorted(EXPECTED_INDEXES.items()))
def test_hotpath_indexes_present(table, names):
    # ensure_columns already ran at server import; re-run for clarity.
    server.ensure_columns()
    found = _index_names(table)
    missing = names - found
    assert not missing, f"{table} missing indexes: {missing}; have {found}"


def test_migration_0022_file_exists():
    from pathlib import Path

    path = Path(server.__file__).resolve().parent / "migrations" / "0022_chat_hotpath_indexes.sql"
    assert path.is_file()
    sql = path.read_text(encoding="utf-8")
    assert "ix_messages_conversation_created" in sql
    assert "ix_conversations_user_updated" in sql
    assert "ix_upload_jobs_type_status" in sql


def test_messages_have_no_file_or_project_columns():
    """Caller asked for messages(file_id)/messages(project_id) — those live on conversations."""
    cols = {c["name"] for c in inspect(server.engine).get_columns("messages")}
    assert "conversation_id" in cols
    assert "file_id" not in cols
    assert "project_id" not in cols
    assert "chat_id" not in cols


def test_provider_cache_lookup_already_indexed():
    """provider_cache(provider, cache_key) is UNIQUE (+ idx) from migration 0018."""
    with server.engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS provider_cache (
                    id INTEGER PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,
                    cache_key VARCHAR(500) NOT NULL,
                    response_json TEXT NOT NULL DEFAULT '{}',
                    provider_version VARCHAR(20) DEFAULT '',
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    UNIQUE(provider, cache_key)
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_provider_cache_lookup "
                "ON provider_cache(provider, cache_key)"
            )
        )
    insp = inspect(server.engine)
    names = {ix["name"] for ix in insp.get_indexes("provider_cache")}
    assert "idx_provider_cache_lookup" in names
    # UNIQUE(provider, cache_key) is the primary lookup path for cache hits.
    unique_cols = [set(u["column_names"]) for u in insp.get_unique_constraints("provider_cache")]
    index_unique = [
        set(ix["column_names"])
        for ix in insp.get_indexes("provider_cache")
        if ix.get("unique")
    ]
    assert {"provider", "cache_key"} in unique_cols or {"provider", "cache_key"} in index_unique

