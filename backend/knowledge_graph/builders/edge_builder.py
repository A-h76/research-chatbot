"""Shared helpers for edge construction."""

from datetime import datetime, timezone
from typing import Any, Optional

from backend.document_understanding.models import EvidenceReference

from ..enums import EdgeDirection, EdgeType
from ..models import GraphEdge, new_id
from ..security.sanitizers import LabelSanitizer, sanitize_properties


class EdgeBuilderHelper:
    def __init__(self, sanitize: bool = True) -> None:
        self._sanitize = sanitize
        self._sanitizer = LabelSanitizer()

    def make_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_type: EdgeType,
        confidence: float,
        label: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
        evidence: Optional[list[EvidenceReference]] = None,
        direction: EdgeDirection = EdgeDirection.DIRECTED,
        inferred: bool = False,
    ) -> GraphEdge:
        props = dict(properties or {})
        if inferred:
            props["inferred"] = True
        if self._sanitize:
            props = sanitize_properties(props)
        edge_label = label or edge_type.value
        if self._sanitize:
            edge_label = self._sanitizer.sanitize(edge_label)
        return GraphEdge(
            edge_id=new_id(),
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            label=edge_label,
            properties=props,
            direction=direction,
            evidence_references=[r for r in (evidence or []) if r is not None],
            confidence=max(0.0, min(1.0, confidence)),
            created_at=datetime.now(timezone.utc),
        )
