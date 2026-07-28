from __future__ import annotations

import logging


def get_writing_logger() -> logging.Logger:
    """Domain logger namespace for writing services."""
    return logging.getLogger("backend.writing")


def log_writing_metric(name: str, **fields) -> None:
    get_writing_logger().info(
        "writing_metric",
        extra={"writing_metric": {"name": name, **fields}},
    )

