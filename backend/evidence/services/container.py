"""DI container primitives for Evidence Layer (BE-0)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceServices:
    SessionLocal: Any
    dependencies: dict[str, Any]


def build_evidence_services(*, SessionLocal: Any, **dependencies: Any) -> EvidenceServices:
    return EvidenceServices(SessionLocal=SessionLocal, dependencies=dependencies)
