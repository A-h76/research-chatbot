"""ModelRouter — task_name -> model string, the *policy* of which model a
task should use. Distinct from ModelRegistry (model_registry.py), which
decides *how* to actually call whatever model string it's given
(provider dispatch, retries) — the two compose:
`registry.call(router.get_model_for_task("paper_analysis"), messages, ...)`.
See docs/prompt-engine-architecture.md §6.

No DB session and no private Base: this is pure config (a dict) plus an
in-memory override map, so it's safe to construct exactly once at
startup and share across every request — unlike PromptRegistry/
ModelRegistry, which each hold a Session for their own lifetime and are
built fresh per request for exactly that reason. `set_model_for_task()`
overrides are process-lifetime only, not persisted: two OS processes
(server.py, worker.py) each get their own ModelRouter instance and their
own overrides, and a restart forgets them — if persistence across a
restart is ever a real requirement, that's a small, separate table
(a `model_routes` table), not something this class does; nothing in this
task implies it's needed yet.
"""
import os
from typing import Dict


class ModelRouter:
    def __init__(self, defaults: Dict[str, str]):
        """`defaults` maps task_name -> model string, plus a required
        "_default" key used for any task_name not otherwise listed (and
        not covered by an override or env var either)."""
        self.defaults = defaults
        self._overrides: Dict[str, str] = {}

    def get_model_for_task(self, task_name: str) -> str:
        """Precedence: in-memory override > {TASK_NAME}_MODEL env var >
        defaults[task_name] > defaults["_default"]."""
        if task_name in self._overrides:
            return self._overrides[task_name]

        env_value = os.environ.get(f"{task_name.upper()}_MODEL")
        if env_value:
            return env_value

        if task_name in self.defaults:
            return self.defaults[task_name]

        return self.defaults["_default"]

    def set_model_for_task(self, task_name: str, model_name: str) -> None:
        self._overrides[task_name] = model_name

    def clear_override(self, task_name: str) -> None:
        self._overrides.pop(task_name, None)
