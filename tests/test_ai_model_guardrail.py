"""Guardrail: no direct model literals in feature code.

Model selection must go through AI Gateway / router policy.
"""

from __future__ import annotations

import re
from pathlib import Path


LITERAL_MODEL_RE = re.compile(r'model\s*=\s*["\'](?:gpt-|claude-|gemini-|o1|o3|o4)')

# Infra modules are allowed to talk in provider-model terms.
ALLOWED = {
    Path("backend/ai/model_registry.py"),
    Path("backend/ai/gateway.py"),
    Path("backend/ai/model_router.py"),
}


def test_no_direct_model_literals_outside_ai_infra():
    root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []

    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if "test" in rel.parts or rel.name.startswith("test_"):
            continue
        if rel in ALLOWED:
            continue
        if rel.parts and rel.parts[0] not in {"backend", "worker.py", "server.py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if LITERAL_MODEL_RE.search(text):
            offenders.append(str(rel))

    assert not offenders, f"Direct model literals found outside AI infra: {offenders}"
