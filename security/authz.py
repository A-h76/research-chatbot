"""Project ownership helpers for write/read paths (PR2).

Does not change PromptBuilder assembly — call sites enforce ownership before
passing project context into prompts or persisting project_id FKs.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple


def resolve_owned_project_id(
    db: Any,
    Project: Any,
    project_id: Any,
    user_id: int,
) -> Tuple[Optional[int], bool]:
    """Return ``(owned_id_or_None, denied)``.

    ``denied`` is True when a non-empty ``project_id`` was supplied but the
    project is missing or owned by someone else. Callers should log
    ``authz_denied`` when ``denied`` is True.
    """
    if project_id is None or project_id == "" or project_id is False:
        return None, False
    try:
        pid = int(project_id)
    except (TypeError, ValueError):
        return None, True
    if pid <= 0:
        return None, False

    project = db.get(Project, pid)
    if project is None:
        return None, True
    owner = getattr(project, "user_id", None)
    if owner is None or int(owner) != int(user_id):
        return None, True
    return pid, False


def project_owned_by_user(project: Any, user_id: int) -> bool:
    """True when ``project`` exists and ``project.user_id == user_id``."""
    if project is None:
        return False
    owner = getattr(project, "user_id", None)
    if owner is None:
        return False
    return int(owner) == int(user_id)
