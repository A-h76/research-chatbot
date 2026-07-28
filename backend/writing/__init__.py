"""Writing domain package (Week 1 foundation).

Stage 2 Slice 0:
- repository and service scaffolding
- shared error taxonomy
- validation and transition guards
- dependency injection container primitives
"""

from .api.errors import WritingDomainError, ErrorCode
from .validation.guards import ensure_transition_allowed

__all__ = [
    "WritingDomainError",
    "ErrorCode",
    "ensure_transition_allowed",
]

