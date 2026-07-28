from __future__ import annotations

from backend.writing.services.logging import get_writing_logger

logger = get_writing_logger()


def publish_writing_event(event) -> None:
    """Slice E baseline publisher.

    Current implementation logs structured event metadata. Later slices can
    fan this out to queues/subscribers without changing call sites.
    """
    logger.info(
        "writing_event",
        extra={
            "writing_event": {
                "name": event.name,
                "user_id": event.user_id,
                "document_id": event.document_id,
                "metadata": event.metadata,
                "created_at": event.created_at,
            }
        },
    )

