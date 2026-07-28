"""Project workspace bounded context.

Sprint A: ProjectService + hub read model + research questions.
Routes are thin Flask adapters; do not ``import server``.
"""

from .service import ProjectService, create_project_service

__all__ = ["ProjectService", "create_project_service"]
