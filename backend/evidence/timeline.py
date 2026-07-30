"""Research Timeline (RI-007) — topic evolution by year.

Anchors every bucket to paper years and/or evidence-derived years.
Never invents papers; undated items go to ``undated``.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from backend.evidence.themes import discover_themes, reconstruct_fingerprint

TIMELINE_VERSION = "1.0.0"
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def resolve_year(
    *,
    paper_year: str | int | None = None,
    obj: dict[str, Any] | None = None,
) -> int | None:
    """Prefer paper metadata year, then provenance, then claim/quote text."""
    if paper_year is not None and str(paper_year).strip():
        try:
            y = int(str(paper_year).strip()[:4])
            if 1900 <= y <= 2100:
                return y
        except ValueError:
            pass
    if not obj:
        return None
    prov = obj.get("provenance") if isinstance(obj.get("provenance"), dict) else {}
    for key in ("year", "publication_year", "pub_year"):
        raw = obj.get(key) if key in (obj or {}) else prov.get(key)
        if raw is None:
            continue
        try:
            y = int(raw)
            if 1900 <= y <= 2100:
                return y
        except (TypeError, ValueError):
            pass
    text = f"{obj.get('claim') or ''} {obj.get('quote') or ''}"
    m = _YEAR_RE.search(text)
    return int(m.group(0)) if m else None


def build_timeline(
    *,
    project_id: int,
    papers: list[dict[str, Any]],
    evidence_objects: list[dict[str, Any]],
    themes_payload: dict[str, Any] | None = None,
    max_samples_per_bucket: int = 3,
) -> dict[str, Any]:
    objs = [o for o in evidence_objects if o.get("id") is not None]
    objs.sort(key=lambda o: int(o["id"]))
    themes_payload = themes_payload or discover_themes(objs, project_id=project_id)
    theme_fp = reconstruct_fingerprint(themes_payload)

    # evidence_id → theme ids
    eid_to_themes: dict[int, list[str]] = defaultdict(list)
    theme_labels: dict[str, str] = {}
    for theme in themes_payload.get("themes") or []:
        tid = str(theme.get("id") or "")
        if not tid:
            continue
        theme_labels[tid] = str(theme.get("label") or tid)
        for eid in theme.get("evidence_ids") or []:
            eid_to_themes[int(eid)].append(tid)

    paper_by_id = {
        int(p.get("file_id") or p.get("id")): p for p in papers if (p.get("file_id") or p.get("id"))
    }
    paper_year: dict[int, int | None] = {}
    for fid, p in paper_by_id.items():
        paper_year[fid] = resolve_year(paper_year=p.get("year"))

    # Buckets: year -> aggregations
    buckets: dict[int | None, dict[str, Any]] = {}

    def bucket(year: int | None) -> dict[str, Any]:
        if year not in buckets:
            buckets[year] = {
                "year": year,
                "file_ids": set(),
                "evidence_ids": [],
                "theme_ids": set(),
                "study_types": set(),
                "samples": [],
            }
        return buckets[year]

    for o in objs:
        eid = int(o["id"])
        fid = int(o["file_id"]) if o.get("file_id") is not None else None
        y = None
        if fid is not None and fid in paper_year and paper_year[fid] is not None:
            y = paper_year[fid]
        if y is None:
            y = resolve_year(obj=o)
        b = bucket(y)
        b["evidence_ids"].append(eid)
        if fid is not None:
            b["file_ids"].add(fid)
        for tid in eid_to_themes.get(eid, []):
            b["theme_ids"].add(tid)
        st = (o.get("study_type") or "").strip()
        if st:
            b["study_types"].add(st)
        if len(b["samples"]) < max_samples_per_bucket:
            b["samples"].append(
                {
                    "evidence_id": eid,
                    "file_id": fid,
                    "claim": (o.get("claim") or o.get("quote") or "")[:240],
                    "theme_ids": list(eid_to_themes.get(eid, [])),
                }
            )

    # Papers with year but no evidence still appear as anchors
    for fid, y in paper_year.items():
        b = bucket(y)
        b["file_ids"].add(fid)

    dated = sorted((y for y in buckets if y is not None))
    undated = buckets.get(None)

    entries: list[dict[str, Any]] = []
    for y in dated:
        b = buckets[y]
        entries.append(
            {
                "year": y,
                "file_ids": sorted(b["file_ids"]),
                "evidence_ids": b["evidence_ids"],
                "theme_ids": sorted(b["theme_ids"]),
                "theme_labels": [theme_labels[t] for t in sorted(b["theme_ids"]) if t in theme_labels],
                "study_types": sorted(b["study_types"]),
                "paper_count": len(b["file_ids"]),
                "evidence_count": len(b["evidence_ids"]),
                "sample_claims": b["samples"],
            }
        )

    undated_payload = None
    if undated and (undated["evidence_ids"] or undated["file_ids"]):
        undated_payload = {
            "year": None,
            "file_ids": sorted(undated["file_ids"]),
            "evidence_ids": undated["evidence_ids"],
            "theme_ids": sorted(undated["theme_ids"]),
            "theme_labels": [
                theme_labels[t] for t in sorted(undated["theme_ids"]) if t in theme_labels
            ],
            "study_types": sorted(undated["study_types"]),
            "paper_count": len(undated["file_ids"]),
            "evidence_count": len(undated["evidence_ids"]),
            "sample_claims": undated["samples"],
        }

    # Evolution: themes first/last seen
    theme_span: dict[str, dict[str, Any]] = {}
    for entry in entries:
        for tid in entry["theme_ids"]:
            span = theme_span.setdefault(
                tid,
                {
                    "theme_id": tid,
                    "label": theme_labels.get(tid, tid),
                    "first_year": entry["year"],
                    "last_year": entry["year"],
                    "years": [],
                },
            )
            span["last_year"] = entry["year"]
            span["years"].append(entry["year"])

    evolution = sorted(
        theme_span.values(),
        key=lambda s: (s["first_year"], s["theme_id"]),
    )

    input_hash = hashlib.sha256(
        json.dumps(
            {
                "theme_fp": theme_fp,
                "years": dated,
                "evidence_ids": [int(o["id"]) for o in objs],
                "paper_years": {str(k): v for k, v in sorted(paper_year.items())},
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "stage": "timeline",
        "timeline_version": TIMELINE_VERSION,
        "project_id": int(project_id),
        "run": {
            "input_hash": input_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sources": ["papers", "evidence_objects", "themes"],
            "themes_fingerprint": theme_fp,
        },
        "span": {
            "start_year": dated[0] if dated else None,
            "end_year": dated[-1] if dated else None,
            "year_count": len(dated),
        },
        "entries": entries,
        "undated": undated_payload,
        "evolution": evolution,
        "metrics": {
            "dated_evidence": sum(e["evidence_count"] for e in entries),
            "undated_evidence": (undated_payload or {}).get("evidence_count") or 0,
            "paper_count": len(paper_by_id),
            "theme_span_count": len(evolution),
        },
    }


def timeline_to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Research Timeline (project {payload.get('project_id')})",
        "",
        f"_timeline_version {payload.get('timeline_version')} · "
        f"span {(payload.get('span') or {}).get('start_year')}–"
        f"{(payload.get('span') or {}).get('end_year')}_",
        "",
    ]
    for entry in payload.get("entries") or []:
        lines.append(f"## {entry.get('year')}")
        lines.append("")
        lines.append(
            f"- Papers: {entry.get('paper_count')} · Evidence: {entry.get('evidence_count')}"
        )
        if entry.get("theme_labels"):
            lines.append(f"- Themes: {', '.join(entry['theme_labels'])}")
        if entry.get("study_types"):
            lines.append(f"- Designs: {', '.join(entry['study_types'])}")
        for s in entry.get("sample_claims") or []:
            lines.append(f"  - [e:{s.get('evidence_id')}] {s.get('claim')}")
        lines.append("")
    undated = payload.get("undated")
    if undated:
        lines.append("## Undated")
        lines.append("")
        lines.append(
            f"- Papers: {undated.get('paper_count')} · Evidence: {undated.get('evidence_count')}"
        )
        lines.append("")
    if payload.get("evolution"):
        lines.append("## Theme evolution")
        lines.append("")
        for span in payload["evolution"]:
            lines.append(
                f"- {span.get('label')}: {span.get('first_year')}→{span.get('last_year')}"
            )
        lines.append("")
    return "\n".join(lines)
