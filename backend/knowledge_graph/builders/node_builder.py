"""Shared helpers for node construction."""

from datetime import datetime, timezone
from typing import Any, Optional

from backend.document_understanding.models import EvidenceReference

from ..enums import NodeType
from ..models import GraphNode, new_id
from ..security.sanitizers import LabelSanitizer, sanitize_properties


class NodeBuilderHelper:
    """Concrete helpers used by specialized node builders."""

    def __init__(self, sanitize: bool = True, max_label_length: int = 500) -> None:
        self._sanitize = sanitize
        self._sanitizer = LabelSanitizer(max_label_length)

    def make_node(
        self,
        node_type: NodeType,
        label: str,
        confidence: float,
        properties: Optional[dict[str, Any]] = None,
        evidence: Optional[list[EvidenceReference]] = None,
        source_entity_id: Optional[str] = None,
    ) -> GraphNode:
        clean_label = self._sanitizer.sanitize(label) if self._sanitize else (label or "")
        props = sanitize_properties(properties or {}) if self._sanitize else dict(properties or {})
        refs = [r for r in (evidence or []) if r is not None]
        return GraphNode(
            node_id=new_id(),
            node_type=node_type,
            label=clean_label or node_type.value,
            properties=props,
            evidence_references=refs,
            confidence=max(0.0, min(1.0, confidence)),
            source_entity_id=source_entity_id,
            created_at=datetime.now(timezone.utc),
        )
