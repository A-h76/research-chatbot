"""ORM helpers for Connect Library tokens + Library collections + sync runs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)


def create_library_connection_model(Base):
    class LibraryConnection(Base):
        __tablename__ = "library_connections"
        __table_args__ = (
            UniqueConstraint("user_id", "provider", name="uq_library_connections_user_provider"),
        )

        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False, index=True)
        provider = Column(String(30), nullable=False)  # zotero|mendeley
        external_user_id = Column(String(100), default="")
        access_token = Column(Text, default="")
        access_secret = Column(Text, default="")  # OAuth1 token secret (Zotero)
        refresh_token = Column(Text, default="")  # OAuth2 (Mendeley)
        meta_json = Column(Text, default="{}")  # username, library type, etc.
        status = Column(String(20), default="active")  # active|revoked
        last_synced_at = Column(DateTime, nullable=True)
        sync_cursor = Column(Text, default="")  # provider opaque cursor / version JSON
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        )

    return LibraryConnection


def create_library_sync_run_model(Base):
    class LibrarySyncRun(Base):
        __tablename__ = "library_sync_runs"

        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False, index=True)
        connection_id = Column(Integer, nullable=True, index=True)
        provider = Column(String(30), nullable=False)
        status = Column(String(20), default="running")  # running|ok|error
        started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        finished_at = Column(DateTime, nullable=True)
        created_count = Column(Integer, default=0)
        updated_count = Column(Integer, default=0)
        skipped_count = Column(Integer, default=0)
        conflict_count = Column(Integer, default=0)
        cursor_before = Column(Text, default="")
        cursor_after = Column(Text, default="")
        error_text = Column(Text, default="")
        detail_json = Column(Text, default="{}")

    return LibrarySyncRun


def create_library_collection_models(Base):
    """Library folders — papers belong to Library; collections reference them."""

    class LibraryCollection(Base):
        __tablename__ = "library_collections"

        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False, index=True)
        name = Column(String(200), nullable=False)
        description = Column(Text, default="")
        parent_id = Column(Integer, nullable=True, index=True)
        external_id = Column(String(100), default="")  # Zotero collection key
        source = Column(String(30), default="manual")  # manual|zotero|mendeley|import
        sort_order = Column(Integer, default=0)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        )

    class LibraryCollectionPaper(Base):
        __tablename__ = "library_collection_papers"
        __table_args__ = (
            UniqueConstraint("collection_id", "file_id", name="uq_collection_paper"),
        )

        id = Column(Integer, primary_key=True)
        collection_id = Column(Integer, nullable=False, index=True)
        file_id = Column(Integer, nullable=False, index=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return LibraryCollection, LibraryCollectionPaper
