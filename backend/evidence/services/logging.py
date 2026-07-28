from __future__ import annotations

import logging


def get_evidence_logger() -> logging.Logger:
    return logging.getLogger("backend.evidence")


def log_evidence_metric(name: str, **fields) -> None:
    # Avoid logging full quotes — callers must not pass quote/claim text here.
    safe = {k: v for k, v in fields.items() if k not in {"quote", "claim", "selected_text"}}
    get_evidence_logger().info(
        "evidence_metric",
        extra={"evidence_metric": {"name": name, **safe}},
    )
