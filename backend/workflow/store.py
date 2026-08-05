"""In-process workflow instance store (inspectable; process-local)."""

from __future__ import annotations

from threading import Lock
from typing import Iterable

from backend.workflow.instance import WorkflowInstance


class WorkflowStore:
    """Thread-safe memory store — sufficient for sync monolith inspectability.

    Durable trail remains WorkflowEvent breadcrumbs + domain events; this store
    is the live step/state picture for open journeys.
    """

    def __init__(self, *, max_instances: int = 20_000) -> None:
        self._by_id: dict[str, WorkflowInstance] = {}
        self._by_file: dict[tuple[int, int], str] = {}  # (user_id, file_id) → workflow_id
        self._max = max_instances
        self._lock = Lock()

    def put(self, instance: WorkflowInstance) -> WorkflowInstance:
        with self._lock:
            self._by_id[instance.workflow_id] = instance
            if instance.file_id is not None:
                self._by_file[(instance.user_id, instance.file_id)] = instance.workflow_id
            self._evict_if_needed()
            return instance

    def get(self, workflow_id: str) -> WorkflowInstance | None:
        with self._lock:
            return self._by_id.get(workflow_id)

    def get_by_file(self, user_id: int, file_id: int) -> WorkflowInstance | None:
        with self._lock:
            wid = self._by_file.get((int(user_id), int(file_id)))
            return self._by_id.get(wid) if wid else None

    def list_for_user(
        self,
        user_id: int,
        *,
        project_id: int | None = None,
        limit: int = 50,
    ) -> list[WorkflowInstance]:
        with self._lock:
            rows = [i for i in self._by_id.values() if i.user_id == int(user_id)]
        if project_id is not None:
            rows = [i for i in rows if i.project_id == int(project_id)]
        rows.sort(key=lambda i: i.updated_at, reverse=True)
        return rows[: max(1, min(limit, 200))]

    def list_for_project(self, user_id: int, project_id: int) -> list[WorkflowInstance]:
        return self.list_for_user(user_id, project_id=project_id, limit=200)

    def all(self) -> Iterable[WorkflowInstance]:
        with self._lock:
            return list(self._by_id.values())

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_file.clear()

    def _evict_if_needed(self) -> None:
        if len(self._by_id) <= self._max:
            return
        # Drop oldest completed first, then oldest overall.
        items = sorted(self._by_id.values(), key=lambda i: i.updated_at)
        while len(self._by_id) > self._max and items:
            old = items.pop(0)
            self._by_id.pop(old.workflow_id, None)
            if old.file_id is not None:
                self._by_file.pop((old.user_id, old.file_id), None)
