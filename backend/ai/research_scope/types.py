"""Research Scope vocabulary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

RS_VERSION = "0.1"
RS_STATUS = "platform_layer"


class ScopeVerdict(str, Enum):
    ALLOW = "allow"
    CLARIFY = "clarify"
    DECLINE = "decline"


@dataclass(frozen=True)
class ScopeDecision:
    verdict: ScopeVerdict
    reason_codes: tuple[str, ...] = ()
    user_message: str = ""
    router_version: str = RS_VERSION

    @property
    def blocks_llm(self) -> bool:
        return self.verdict in (ScopeVerdict.DECLINE, ScopeVerdict.CLARIFY)

    def to_gate_dict(self) -> dict[str, Any]:
        return {
            "scope_gate": {
                "verdict": self.verdict.value,
                "reason_codes": list(self.reason_codes),
                "router_version": self.router_version,
            }
        }
