"""Idempotency helpers for domain event handlers."""

from __future__ import annotations

from threading import Lock
from typing import Callable

from backend.domain_events.types import DomainEvent

Handler = Callable[[DomainEvent], None]


class IdempotencyStore:
    """In-process set of (handler_key, event_id) pairs already delivered.

    Process-local only — sufficient for a sync monolith. Surviving across
    workers would require durable storage (out of scope; not Kafka).
    """

    def __init__(self, *, max_entries: int = 50_000) -> None:
        self._seen: set[tuple[str, str]] = set()
        self._order: list[tuple[str, str]] = []
        self._max = max_entries
        self._lock = Lock()

    def already_processed(self, handler_key: str, event_id: str) -> bool:
        with self._lock:
            return (handler_key, event_id) in self._seen

    def mark_processed(self, handler_key: str, event_id: str) -> None:
        key = (handler_key, event_id)
        with self._lock:
            if key in self._seen:
                return
            self._seen.add(key)
            self._order.append(key)
            while len(self._order) > self._max:
                old = self._order.pop(0)
                self._seen.discard(old)

    def clear(self) -> None:
        with self._lock:
            self._seen.clear()
            self._order.clear()


def wrap_idempotent(handler: Handler, *, handler_key: str, store: IdempotencyStore) -> Handler:
    """Skip handler if ``(handler_key, event.event_id)`` was already delivered."""

    def _wrapped(event: DomainEvent) -> None:
        if store.already_processed(handler_key, event.event_id):
            return
        handler(event)
        store.mark_processed(handler_key, event.event_id)

    _wrapped.__name__ = getattr(handler, "__name__", "handler")  # type: ignore[attr-defined]
    _wrapped.__idempotent_key__ = handler_key  # type: ignore[attr-defined]
    return _wrapped
