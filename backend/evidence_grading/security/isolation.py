"""Plugin isolation — allowlist enforcement plus a best-effort execution
timeout for any callable this pipeline treats as a "plugin" (a grader or
assessor a caller registered beyond this package's own defaults).

Allowlist semantics: an EMPTY plugin_allowlist means unrestricted, not
deny-everything. Read literally, the task's own default
(`plugin_allowlist: list[str] = field(default_factory=list)`) combined
with a strict "reject anything not in the allowlist" check would block
every one of this pipeline's own default-registered assessors/graders on
a fresh EvidenceGradingConfig() — see config.py's own module docstring
for this same decision. Populating plugin_allowlist with specific names
is what actually turns the restriction on.

Timeout: real, cross-platform wall-clock enforcement of a hard timeout
isn't possible for a blocking Python call without killing a thread
(unsafe) or a process (heavyweight) — same conclusion backend.
medical_understanding's own RegexGuard reached for regex timeouts. This
uses the identical best-effort pattern: run on a daemon thread, stop
waiting after timeout_ms. A plugin that truly never returns keeps
running in the background (daemon=True means it can never block process
exit) rather than hanging the caller.
"""

import threading
from typing import Any, Callable

from ..config import EvidenceGradingConfig
from ..exceptions import GradingTimeoutError, SecurityError


class PluginIsolator:
    """See module docstring."""

    def __init__(self, config: EvidenceGradingConfig) -> None:
        self.timeout_ms = config.plugin_timeout_ms
        self.allowlist = config.plugin_allowlist
        self.sandbox_enabled = config.plugin_sandbox_enabled

    def execute_plugin(self, plugin_name: str, fn: Callable, *args: Any) -> Any:
        if self.allowlist and plugin_name not in self.allowlist:
            raise SecurityError(f"plugin {plugin_name!r} is not in the configured allowlist")

        if not self.sandbox_enabled:
            return fn(*args)

        return self._run_with_timeout(fn, args)

    def _run_with_timeout(self, fn: Callable, args: tuple) -> Any:
        result: list = [None]
        raised: list = [None]

        def _run() -> None:
            try:
                result[0] = fn(*args)
            except Exception as exc:  # noqa: BLE001 -- re-raised on the caller's thread below
                raised[0] = exc

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout_ms / 1000)
        if thread.is_alive():
            raise GradingTimeoutError(f"plugin exceeded {self.timeout_ms}ms timeout")
        if raised[0] is not None:
            raise raised[0]
        return result[0]
