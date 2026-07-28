"""Writing domain event primitives."""

from .event_types import WritingEvent, make_writing_event
from .publisher import publish_writing_event

__all__ = ["WritingEvent", "make_writing_event", "publish_writing_event"]

