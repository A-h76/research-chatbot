"""Safe regex compilation and matching.

Real, cross-platform wall-clock enforcement of a regex timeout isn't
possible with stdlib `re` alone — there's no portable way to interrupt a
blocking C-level match call (signal-based timeouts are POSIX-only; this
environment is Windows). This module does two real things instead:

1. Pattern-safety checks before compiling at all (length cap, a
   heuristic for the nested-quantifier shapes that cause catastrophic
   backtracking, e.g. `(a+)+`) — the actual ReDoS-prevention layer,
   since every pattern used throughout this package is a simple,
   hand-written literal/alternation (matching backend.classification.
   pass2's own deterministic keyword-matching style), not a scenario a
   wall-clock timeout should be the first line of defense against.
2. A best-effort timeout: the match runs on a daemon thread, and the
   caller stops waiting after `timeout_ms`. The thread is NOT killed
   (Python has no safe way to do that) — on a truly pathological
   pattern it keeps running in the background until it finishes or the
   process exits (daemon=True means it can never block process exit
   the way a non-daemon thread pool would). Given (1) already rejects
   the pattern shapes that would cause this, this path should
   essentially never fire in practice.
"""

import re
import threading
from typing import Optional

# A repeated group directly followed by another repetition — the
# classic catastrophic-backtracking shape (e.g. `(a+)+`, `(a*)+`).
_NESTED_QUANTIFIER_RE = re.compile(r"\([^()]*[+*][^()]*\)[+*]")


class RegexGuard:
    """Compiles and runs regexes defensively — see module docstring."""

    def __init__(self, timeout_ms: int = 100, max_pattern_length: int = 1000) -> None:
        self.timeout_ms = timeout_ms
        self.max_pattern_length = max_pattern_length
        self._compiled_cache: dict[str, Optional[re.Pattern]] = {}

    def safe_compile(self, pattern: str) -> Optional[re.Pattern]:
        """Compiles `pattern`, or returns None if it fails a safety
        check or fails to compile — never raises. Cached by pattern
        string."""
        if pattern not in self._compiled_cache:
            self._compiled_cache[pattern] = self._compile(pattern)
        return self._compiled_cache[pattern]

    def _compile(self, pattern: str) -> Optional[re.Pattern]:
        if len(pattern) > self.max_pattern_length:
            return None
        if _NESTED_QUANTIFIER_RE.search(pattern):
            return None
        try:
            return re.compile(pattern, re.IGNORECASE)
        except re.error:
            return None

    def safe_search(self, pattern: re.Pattern, text: str) -> Optional[re.Match]:
        return self._run_with_timeout(pattern.search, text)

    def safe_finditer(self, pattern: re.Pattern, text: str) -> list[re.Match]:
        return self._run_with_timeout(lambda t: list(pattern.finditer(t)), text) or []

    def _run_with_timeout(self, fn, text: str):
        result: list = [None]

        def _run() -> None:
            result[0] = fn(text)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout_ms / 1000)
        if thread.is_alive():
            return None
        return result[0]
