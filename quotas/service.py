"""Quota checking/tracking, constructor-injected (SessionLocal, User,
StorageUsage, UsageLog, select) rather than `import server` — same
reason as quotas/models.py and every auth/ module: server.py runs as
__main__, and a module it reaches into importing "server" back re-runs
the whole file under a second module identity.

Storage usage is read from the existing StorageUsage table (already the
live source of truth, maintained since the transactional-outbox upload
path), never duplicated here — see this task's own note on why
`storage_used_bytes` was deliberately not added to User. Only the
per-user *limit* is new.
"""
from datetime import datetime, timezone, timedelta


class QuotaExceededError(Exception):
    """Raised by check_storage_quota()/check_token_quota() — a plain
    domain exception, not tied to Flask; callers decide the HTTP
    response (403, etc.)."""
    def __init__(self, message, kind, used, limit):
        super().__init__(message)
        self.kind = kind          # "storage" | "tokens"
        self.used = used
        self.limit = limit


class QuotaService:
    DEFAULT_STORAGE_LIMIT_BYTES = 1_000_000_000   # ~1GB, free tier
    DEFAULT_TOKEN_LIMIT = 100_000                  # free tier, per month
    RESET_PERIOD = timedelta(days=30)

    def __init__(self, SessionLocal, User, StorageUsage, UsageLog, select,
                now_fn=lambda: datetime.now(timezone.utc)):
        self.SessionLocal = SessionLocal
        self.User = User
        self.StorageUsage = StorageUsage
        self.UsageLog = UsageLog
        self.select = select
        # Injected, not called directly as datetime.now(timezone.utc)
        # inline, specifically so tests can mock "now" for the monthly
        # reset logic without waiting 30 real days.
        self._now = now_fn

    # ------------------------------------------------------------ internal
    def _get_user(self, db, user_id):
        user = db.get(self.User, user_id)
        if not user:
            raise ValueError(f"no such user: {user_id}")
        return user

    def _ensure_reset(self, db, user):
        """Lazy monthly rollover: checked at the top of every
        token-quota operation rather than on a schedule, so a user who's
        inactive for months doesn't need a cron job to catch up — the
        reset just happens the next time they actually do something."""
        now = self._now()
        reset_at = user.quota_reset_at
        # SQLite doesn't preserve tzinfo across a round-trip — a value
        # written as UTC-aware comes back naive on the next read. Every
        # write in this class uses UTC, so a naive value here is purely
        # a storage artifact, not a genuine ambiguity about which
        # timezone was meant; without this, comparing it against an
        # aware `now` raises TypeError on SQLite (Postgres's timestamptz
        # doesn't have this problem, but the code shouldn't depend on
        # which backend is running under it).
        if reset_at and reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        if not reset_at or reset_at <= now:
            user.monthly_token_used = 0
            user.quota_reset_at = now + self.RESET_PERIOD
            db.commit()

    def _current_storage_bytes(self, db, user_id):
        usage = db.get(self.StorageUsage, user_id)
        return usage.bytes_used if usage else 0

    # ------------------------------------------------------------ checks
    def check_storage_quota(self, user_id, additional_bytes):
        db = self.SessionLocal()
        try:
            user = self._get_user(db, user_id)
            current = self._current_storage_bytes(db, user_id)
            limit = user.storage_limit_bytes or self.DEFAULT_STORAGE_LIMIT_BYTES
            projected = current + additional_bytes
            if projected > limit:
                raise QuotaExceededError(
                    f"storage quota exceeded: {projected} > {limit} bytes",
                    kind="storage", used=current, limit=limit)
        finally:
            db.close()

    def check_token_quota(self, user_id, token_estimate):
        db = self.SessionLocal()
        try:
            user = self._get_user(db, user_id)
            self._ensure_reset(db, user)
            used = user.monthly_token_used or 0
            limit = user.monthly_token_limit or self.DEFAULT_TOKEN_LIMIT
            projected = used + token_estimate
            if projected > limit:
                raise QuotaExceededError(
                    f"token quota exceeded: {projected} > {limit}",
                    kind="tokens", used=used, limit=limit)
        finally:
            db.close()

    # ------------------------------------------------------------ recording
    # Pure recording — no quota check here. The intended call shape is
    # check_*_quota() first (raises if this operation shouldn't proceed),
    # then the caller does the actual work, then increment_*() records
    # what happened. Re-checking inside increment_* would just repeat
    # the same check for no benefit.
    def increment_storage(self, user_id, bytes_added, delta_files=1):
        """Updates the live StorageUsage counter (the same table
        check_storage_quota() reads) and writes the audit log entry, in
        one transaction. Mirrors server.py's own _adjust_storage_usage()
        get-or-create-then-increment shape — this is the QuotaService
        equivalent, for callers that don't already have a StorageUsage
        row / db session of their own to fold it into."""
        db = self.SessionLocal()
        try:
            self._get_user(db, user_id)   # raises if the user doesn't exist
            usage = db.get(self.StorageUsage, user_id)
            if not usage:
                usage = self.StorageUsage(user_id=user_id, bytes_used=0, file_count=0)
                db.add(usage)
            usage.bytes_used = max(0, (usage.bytes_used or 0) + bytes_added)
            usage.file_count = max(0, (usage.file_count or 0) + delta_files)
            db.add(self.UsageLog(user_id=user_id, action="upload", amount=bytes_added))
            db.commit()
        finally:
            db.close()

    def increment_tokens(self, user_id, tokens_used):
        db = self.SessionLocal()
        try:
            user = self._get_user(db, user_id)
            self._ensure_reset(db, user)
            user.monthly_token_used = (user.monthly_token_used or 0) + tokens_used
            db.add(self.UsageLog(user_id=user_id, action="ai_query", amount=tokens_used))
            db.commit()
        finally:
            db.close()

    # ------------------------------------------------------------ reporting
    def get_usage_summary(self, user_id):
        db = self.SessionLocal()
        try:
            user = self._get_user(db, user_id)
            self._ensure_reset(db, user)

            storage_used = self._current_storage_bytes(db, user_id)
            storage_limit = user.storage_limit_bytes or self.DEFAULT_STORAGE_LIMIT_BYTES
            token_used = user.monthly_token_used or 0
            token_limit = user.monthly_token_limit or self.DEFAULT_TOKEN_LIMIT

            return {
                "storage": {
                    "used_bytes": storage_used,
                    "limit_bytes": storage_limit,
                    "percent": round(100 * storage_used / storage_limit, 2) if storage_limit else 0.0,
                },
                "tokens": {
                    "used": token_used,
                    "limit": token_limit,
                    "percent": round(100 * token_used / token_limit, 2) if token_limit else 0.0,
                    "reset_at": user.quota_reset_at.isoformat() if user.quota_reset_at else None,
                },
            }
        finally:
            db.close()
