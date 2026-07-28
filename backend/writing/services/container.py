from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .logging import get_writing_logger


@dataclass(frozen=True)
class WritingServices:
    """Slice 0 DI container for writing domain dependencies.

    Concrete service implementations are added in later slices.
    """

    SessionLocal: Any
    logger: Any
    dependencies: dict[str, Any]


def build_writing_services(*, SessionLocal: Any, **dependencies: Any) -> WritingServices:
    return WritingServices(
        SessionLocal=SessionLocal,
        logger=get_writing_logger(),
        dependencies=dependencies,
    )

