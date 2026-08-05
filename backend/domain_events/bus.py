"""Internal synchronous Domain Event Bus (Bite 14).

In-process only — no Kafka, RabbitMQ, Redis Pub/Sub, or microservices.
Publish business domain events; handlers run synchronously and must be
idempotent (bus enforces per-handler delivery dedupe by ``event_id``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import Lock
from typing import Callable

from backend.domain_events.catalog import assert_domain_event_name
from backend.domain_events.idempotency import IdempotencyStore, wrap_idempotent
from backend.domain_events.types import DomainEvent

logger = logging.getLogger("backend.domain_events")

Handler = Callable[[DomainEvent], None]


@dataclass(frozen=True)
class _Subscription:
    event_name: str | None  # None = all domain events
    handler: Handler
    handler_key: str


class DomainEventBus:
    """Synchronous in-process publish / subscribe for domain events."""

    def __init__(self, *, idempotency: IdempotencyStore | None = None) -> None:
        self._subs: list[_Subscription] = []
        self._lock = Lock()
        self._idempotency = idempotency or IdempotencyStore()
        self._publish_failures = 0

    @property
    def idempotency(self) -> IdempotencyStore:
        return self._idempotency

    def subscribe(
        self,
        handler: Handler,
        *,
        event_name: str | None = None,
        handler_key: str | None = None,
        idempotent: bool = True,
    ) -> None:
        """Register a handler.

        ``event_name`` — one catalog name, or ``None`` for all domain events.
        ``handler_key`` — stable id for idempotency (defaults to function name).
        ``idempotent`` — wrap with delivery dedupe (default True).
        """
        if event_name is not None:
            assert_domain_event_name(event_name)
        key = handler_key or getattr(handler, "__name__", None) or "anonymous"
        wrapped = wrap_idempotent(handler, handler_key=key, store=self._idempotency) if idempotent else handler
        with self._lock:
            self._subs.append(_Subscription(event_name=event_name, handler=wrapped, handler_key=key))

    def unsubscribe_all(self) -> None:
        with self._lock:
            self._subs.clear()

    def clear(self) -> None:
        """Drop subscriptions and idempotency memory (tests)."""
        self.unsubscribe_all()
        self._idempotency.clear()
        self._publish_failures = 0

    def publish(self, event: DomainEvent) -> int:
        """Deliver ``event`` to matching handlers synchronously.

        Returns the number of handlers invoked (including no-op idempotent skips
        that still enter the wrapper). Handler exceptions are logged and do not
        abort remaining handlers or the caller.
        """
        if not isinstance(event, DomainEvent):
            raise TypeError("publish expects a DomainEvent")
        assert_domain_event_name(event.name)

        with self._lock:
            targets = [s for s in self._subs if s.event_name is None or s.event_name == event.name]

        logger.info(
            "domain_event",
            extra={
                "domain_event": {
                    "name": event.name,
                    "event_id": event.event_id,
                    "correlation_id": event.correlation_id,
                    "payload": event.payload,
                    "occurred_at": event.occurred_at,
                    "handlers": len(targets),
                }
            },
        )

        invoked = 0
        for sub in targets:
            invoked += 1
            try:
                sub.handler(event)
            except Exception:
                self._publish_failures += 1
                logger.exception(
                    "domain_event_handler_failed name=%s handler=%s event_id=%s",
                    event.name,
                    sub.handler_key,
                    event.event_id,
                )
        return invoked


_bus: DomainEventBus | None = None
_bus_lock = Lock()


def get_bus() -> DomainEventBus:
    """Process-wide bus singleton (composition root may replace via ``set_bus``)."""
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = DomainEventBus()
        return _bus


def set_bus(bus: DomainEventBus | None) -> None:
    """Replace the process bus (tests / explicit wiring)."""
    global _bus
    with _bus_lock:
        _bus = bus


def publish(event: DomainEvent) -> int:
    return get_bus().publish(event)


def subscribe(
    handler: Handler,
    *,
    event_name: str | None = None,
    handler_key: str | None = None,
    idempotent: bool = True,
) -> None:
    get_bus().subscribe(
        handler,
        event_name=event_name,
        handler_key=handler_key,
        idempotent=idempotent,
    )
