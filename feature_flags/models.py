"""FeatureFlag ORM factory — binds to server.py's Base, never imports server.

Schema matches migrations/0008_feature_flags.sql and database-design.md §2.11:
user_id NULL = global default; a per-user row overrides it. Partial unique
indexes live in the migration (Postgres); SQLite tests rely on app upsert.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, SmallInteger, Text


def create_feature_flag_model(Base):
    class FeatureFlag(Base):
        __tablename__ = "feature_flags"

        id = Column(Integer, primary_key=True)
        flag_name = Column(Text, nullable=False)
        enabled = Column(Boolean, nullable=False, default=False)
        user_id = Column(Integer, nullable=True)  # NULL = global; FK only in migration
        rollout_pct = Column(SmallInteger, nullable=True)
        updated_at = Column(
            DateTime,
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        )

    return FeatureFlag
