"""Project Knowledge Graph (RI-005) — Evidence-first, no Neo4j.

Nodes: paper · evidence · theme. Edges: from · in_theme · contradicts (from
conflict links when provided) · related (same paper siblings, capped).
Never invents papers or evidence ids.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from backend.evidence.themes import discover_themes, reconstruct_fingerprint

GRAPH_VERSION = "1.0.0"


def _trim(text: str, n: int = 120) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _input_hash(*, evidence_ids: list[int], theme_fp: str, conflict_pairs: list[tuple[int, int]]) -> str:
    raw = json.dumps(
        {
            "evidence_ids": evidence_ids,
            "theme_fp": theme_fp,
            "conflict_pairs": conflict_pairs,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_project_graph(
    *,
    project_id: int,
    papers: list[dict[str, Any]],
    evidence_objects: list[dict[str, Any]],
    themes_payload: dict[str, Any] | None = None,
    conflict_links: list[dict[str, Any]] | None = None,
    max_related_per_paper: int = 8,
) -> dict[str, Any]:
    """Assemble a project-scoped graph over EvidenceObjects (+ themes)."""
    objs = [o for o in evidence_objects if o.get("id") is not None]
    objs.sort(key=lambda o: int(o["id"]))
    by_id = {int(o["id"]): o for o in objs}

    themes_payload = themes_payload or discover_themes(objs, project_id=project_id)
    theme_fp = reconstruct_fingerprint(themes_payload)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[str] = set()

    def add_node(node: dict[str, Any]) -> None:
        nid = node["id"]
        if nid in seen_nodes:
            return
        seen_nodes.add(nid)
        nodes.append(node)

    def add_edge(edge: dict[str, Any]) -> None:
        eid = edge["id"]
        if eid in seen_edges:
            return
        if edge["source"] not in seen_nodes or edge["target"] not in seen_nodes:
            return
        seen_edges.add(eid)
        edges.append(edge)

    # Papers
    paper_by_id: dict[int, dict[str, Any]] = {}
    for p in papers:
        fid = int(p.get("file_id") or p.get("id"))
        paper_by_id[fid] = p
        title = (p.get("title") or p.get("name") or f"Paper #{fid}").strip()
        add_node(
            {
                "id": f"paper:{fid}",
                "type": "paper",
                "label": _trim(title, 80),
                "ref": {
                    "file_id": fid,
                    "year": (p.get("year") or "") or None,
                },
            }
        )

    # Ensure papers exist for evidence file_ids even if not in papers list
    for o in objs:
        fid = o.get("file_id")
        if fid is None:
            continue
        fid = int(fid)
        if f"paper:{fid}" not in seen_nodes:
            add_node(
                {
                    "id": f"paper:{fid}",
                    "type": "paper",
                    "label": f"Paper #{fid}",
                    "ref": {"file_id": fid, "year": None},
                }
            )

    # Evidence nodes + from edges
    for o in objs:
        eid = int(o["id"])
        claim = _trim(o.get("claim") or o.get("quote") or f"Evidence #{eid}")
        fid = int(o["file_id"]) if o.get("file_id") is not None else None
        add_node(
            {
                "id": f"evidence:{eid}",
                "type": "evidence",
                "label": claim,
                "ref": {
                    "evidence_id": eid,
                    "file_id": fid,
                    "page": o.get("page"),
                    "status": o.get("status"),
                    "confidence_band": o.get("confidence_band"),
                },
            }
        )
        if fid is not None:
            add_edge(
                {
                    "id": f"from:paper:{fid}->evidence:{eid}",
                    "source": f"paper:{fid}",
                    "target": f"evidence:{eid}",
                    "type": "from",
                    "evidence_ids": [eid],
                }
            )

    # Theme nodes + in_theme edges
    for theme in themes_payload.get("themes") or []:
        tid = str(theme.get("id") or "")
        if not tid:
            continue
        add_node(
            {
                "id": f"theme:{tid}",
                "type": "theme",
                "label": _trim(theme.get("label") or tid, 100),
                "ref": {
                    "theme_id": tid,
                    "letter": theme.get("letter"),
                    "evidence_ids": list(theme.get("evidence_ids") or []),
                    "size": theme.get("size"),
                },
            }
        )
        for eid in theme.get("evidence_ids") or []:
            eid = int(eid)
            if eid not in by_id:
                continue
            add_edge(
                {
                    "id": f"in_theme:evidence:{eid}->theme:{tid}",
                    "source": f"evidence:{eid}",
                    "target": f"theme:{tid}",
                    "type": "in_theme",
                    "evidence_ids": [eid],
                }
            )

    # Conflict links → contradicts edges (Evidence-first pairwise)
    conflict_pairs: list[tuple[int, int]] = []
    for link in conflict_links or []:
        try:
            a = int(link.get("a_id"))
            b = int(link.get("b_id"))
        except (TypeError, ValueError):
            continue
        if a not in by_id or b not in by_id:
            continue
        lo, hi = (a, b) if a < b else (b, a)
        conflict_pairs.append((lo, hi))
        add_edge(
            {
                "id": f"contradicts:evidence:{lo}<->evidence:{hi}",
                "source": f"evidence:{lo}",
                "target": f"evidence:{hi}",
                "type": "contradicts",
                "evidence_ids": [lo, hi],
                "mediators": list(link.get("mediators") or []),
                "unexplained": bool(link.get("unexplained")),
            }
        )
    conflict_pairs = sorted(set(conflict_pairs))

    # Related: cap siblings on same paper (structural, not semantic invention)
    by_file: dict[int, list[int]] = {}
    for o in objs:
        if o.get("file_id") is None:
            continue
        by_file.setdefault(int(o["file_id"]), []).append(int(o["id"]))
    for fid, eids in sorted(by_file.items()):
        eids = sorted(eids)
        # Connect consecutive ids only to avoid O(n^2) clique
        for i in range(min(len(eids) - 1, max_related_per_paper)):
            a, b = eids[i], eids[i + 1]
            add_edge(
                {
                    "id": f"related:evidence:{a}-evidence:{b}",
                    "source": f"evidence:{a}",
                    "target": f"evidence:{b}",
                    "type": "related",
                    "evidence_ids": [a, b],
                }
            )

    evidence_ids = [int(o["id"]) for o in objs]
    return {
        "stage": "graph",
        "graph_version": GRAPH_VERSION,
        "project_id": int(project_id),
        "run": {
            "input_hash": _input_hash(
                evidence_ids=evidence_ids,
                theme_fp=theme_fp,
                conflict_pairs=conflict_pairs,
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sources": ["evidence_objects", "themes"]
            + (["conflict"] if conflict_pairs else []),
            "themes_version": themes_payload.get("themes_version"),
        },
        "nodes": nodes,
        "edges": edges,
        "metrics": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "paper_count": sum(1 for n in nodes if n["type"] == "paper"),
            "evidence_count": sum(1 for n in nodes if n["type"] == "evidence"),
            "theme_count": sum(1 for n in nodes if n["type"] == "theme"),
            "contradicts_count": sum(1 for e in edges if e["type"] == "contradicts"),
        },
        # Reconstructability helpers (clients may ignore)
        "themes_fingerprint": theme_fp,
    }
