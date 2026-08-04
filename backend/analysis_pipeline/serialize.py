"""JSON-safe serialization for Phase 1 dataclasses (black-box outputs)."""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


def to_jsonable(obj: Any, *, max_str: int | None = None) -> Any:
    """Recursively convert dataclasses / enums / datetimes to JSON types."""
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    # Enum before str — SectionType is a str Enum; isinstance(x, str) would
    # otherwise keep the enum instance and break JSON + downstream heuristics.
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, str):
        if max_str is not None and len(obj) > max_str:
            return obj[:max_str] + f"…[truncated,{len(obj)} chars]"
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k) if not isinstance(k, Enum) else k.value: to_jsonable(v, max_str=max_str) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v, max_str=max_str) for v in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return to_jsonable(asdict(obj), max_str=max_str)
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return to_jsonable(vars(obj), max_str=max_str)
    return str(obj)
