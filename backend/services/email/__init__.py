"""Transactional email package — Resend transport, templates, event dispatch.

Never ``import server``. Call sites inject this service via DI.
"""

from __future__ import annotations

from .events import EmailEvent
from .service import TransactionalEmailService

__all__ = ["EmailEvent", "TransactionalEmailService"]
