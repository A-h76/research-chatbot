"""Evidence Matrix (RI-002) — Paper × Method × Dataset × Findings × Limitations.

Derived from EvidenceObjects (+ optional PaperAnalysis metadata). Never invents
literature: empty cells are explicitly ``unknown`` and cite evidence ids when known.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

MATRIX_VERSION = "1.0.0"
MATRIX_COLUMNS = ("paper", "method", "dataset", "findings", "limitations")

_MAX_FINDINGS = 5
_MAX_LIMITATIONS = 6
_MAX_CELL_CHARS = 600


def _trim(text: str, limit: int = _MAX_CELL_CHARS) -> str:
    t = " ".join((text or "").split())
    if len(t) <= limit:
        return t
    return t[: limit - 1].rstrip() + "…"


def _parse_analysis_data(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _provenance_dataset(obj: dict[str, Any]) -> str:
    prov = obj.get("provenance")
    if not isinstance(prov, dict):
        return ""
    for key in ("dataset", "data_source", "corpus", "sample_source"):
        val = prov.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, list):
            parts = [str(x).strip() for x in val if str(x).strip()]
            if parts:
                return "; ".join(parts[:4])
    return ""


def make_cell(
    *,
    value: str | None,
    evidence_ids: list[int] | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    ids = sorted({int(i) for i in (evidence_ids or []) if i is not None})
    srcs = list(dict.fromkeys(sources or []))
    text = _trim(value) if value and str(value).strip() else ""
    if not text:
        return {
            "value": None,
            "status": "unknown",
            "evidence_ids": [],
            "sources": [],
        }
    return {
        "value": text,
        "status": "known",
        "evidence_ids": ids,
        "sources": srcs,
    }


def _join_unique(parts: list[str], *, limit: int) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        key = p.strip().lower()
        if not p.strip() or key in seen:
            continue
        seen.add(key)
        out.append(p.strip())
        if len(out) >= limit:
            break
    return "; ".join(out)


def build_row_for_paper(
    *,
    file_id: int,
    paper_title: str,
    paper_year: str = "",
    paper_authors: str = "",
    evidence_objects: list[dict[str, Any]],
    analysis_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one matrix row. Prefer EvidenceObject fields; fall back to PaperAnalysis."""
    analysis = analysis_data or {}
    objs = [o for o in evidence_objects if o.get("id") is not None]

    # Method
    method_parts: list[str] = []
    method_ids: list[int] = []
    for o in objs:
        st = (o.get("study_type") or "").strip()
        if st:
            method_parts.append(st)
            method_ids.append(int(o["id"]))
        prov = o.get("provenance") if isinstance(o.get("provenance"), dict) else {}
        pm = (prov.get("method") or "").strip() if isinstance(prov.get("method"), str) else ""
        if pm:
            method_parts.append(pm)
            method_ids.append(int(o["id"]))
    method_text = _join_unique(method_parts, limit=4)
    method_sources: list[str] = []
    if method_text:
        method_sources.append("evidence_object")
    if not method_text:
        method_text = str(analysis.get("methodology") or "").strip()
        if method_text:
            method_sources.append("paper_analysis")

    # Dataset
    dataset_parts: list[str] = []
    dataset_ids: list[int] = []
    for o in objs:
        ds = _provenance_dataset(o)
        if ds:
            dataset_parts.append(ds)
            dataset_ids.append(int(o["id"]))
    dataset_text = _join_unique(dataset_parts, limit=3)
    dataset_sources: list[str] = []
    if dataset_text:
        dataset_sources.append("evidence_object")
    if not dataset_text:
        dataset_text = str(analysis.get("dataset") or "").strip()
        if dataset_text:
            dataset_sources.append("paper_analysis")

    # Findings
    finding_parts: list[str] = []
    finding_ids: list[int] = []
    for o in objs:
        claim = (o.get("claim") or "").strip()
        if claim:
            finding_parts.append(claim)
            finding_ids.append(int(o["id"]))
            continue
        supports = o.get("supports") or []
        if isinstance(supports, list) and supports:
            finding_parts.append("; ".join(str(s).strip() for s in supports[:2] if str(s).strip()))
            finding_ids.append(int(o["id"]))
    findings_text = _join_unique(finding_parts, limit=_MAX_FINDINGS)
    findings_sources: list[str] = []
    if findings_text:
        findings_sources.append("evidence_object")
    if not findings_text:
        for key in ("results", "key_contributions"):
            val = analysis.get(key)
            if isinstance(val, list):
                findings_text = _join_unique([str(x) for x in val], limit=_MAX_FINDINGS)
            elif isinstance(val, str) and val.strip():
                findings_text = val.strip()
            if findings_text:
                findings_sources.append("paper_analysis")
                break

    # Limitations
    lim_parts: list[str] = []
    lim_ids: list[int] = []
    for o in objs:
        lims = o.get("limitations") or []
        if isinstance(lims, list):
            for item in lims:
                s = str(item).strip()
                if s:
                    lim_parts.append(s)
                    lim_ids.append(int(o["id"]))
    limitations_text = _join_unique(lim_parts, limit=_MAX_LIMITATIONS)
    lim_sources: list[str] = []
    if limitations_text:
        lim_sources.append("evidence_object")
    if not limitations_text:
        val = analysis.get("limitations")
        if isinstance(val, list):
            limitations_text = _join_unique([str(x) for x in val], limit=_MAX_LIMITATIONS)
        elif isinstance(val, str) and val.strip():
            limitations_text = val.strip()
        if limitations_text:
            lim_sources.append("paper_analysis")

    title = (paper_title or "").strip() or f"Paper #{file_id}"
    return {
        "file_id": int(file_id),
        "paper_title": title,
        "paper_year": (paper_year or "").strip(),
        "paper_authors": (paper_authors or "").strip(),
        "evidence_count": len(objs),
        "method": make_cell(value=method_text or None, evidence_ids=method_ids, sources=method_sources),
        "dataset": make_cell(
            value=dataset_text or None, evidence_ids=dataset_ids, sources=dataset_sources
        ),
        "findings": make_cell(
            value=findings_text or None, evidence_ids=finding_ids, sources=findings_sources
        ),
        "limitations": make_cell(
            value=limitations_text or None, evidence_ids=lim_ids, sources=lim_sources
        ),
    }


def build_evidence_matrix(
    *,
    project_id: int,
    papers: list[dict[str, Any]],
    evidence_by_file: dict[int, list[dict[str, Any]]],
    analysis_by_file: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble project matrix. ``papers`` items need ``file_id`` / ``id`` and title fields."""
    analysis_by_file = analysis_by_file or {}
    rows: list[dict[str, Any]] = []
    for paper in papers:
        fid = int(paper.get("file_id") or paper.get("id"))
        rows.append(
            build_row_for_paper(
                file_id=fid,
                paper_title=str(paper.get("title") or paper.get("name") or ""),
                paper_year=str(paper.get("year") or ""),
                paper_authors=str(paper.get("authors") or ""),
                evidence_objects=list(evidence_by_file.get(fid) or []),
                analysis_data=_parse_analysis_data(analysis_by_file.get(fid)),
            )
        )

    known = 0
    unknown = 0
    for row in rows:
        for col in ("method", "dataset", "findings", "limitations"):
            if row[col]["status"] == "known":
                known += 1
            else:
                unknown += 1
    cell_total = known + unknown
    coverage = (known / cell_total) if cell_total else None

    return {
        "stage": "matrix",
        "matrix_version": MATRIX_VERSION,
        "project_id": int(project_id),
        "columns": list(MATRIX_COLUMNS),
        "rows": rows,
        "metrics": {
            "paper_count": len(rows),
            "cell_known": known,
            "cell_unknown": unknown,
            "coverage": round(coverage, 4) if coverage is not None else None,
            "papers_with_evidence": sum(1 for r in rows if r["evidence_count"] > 0),
        },
    }


def matrix_to_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        f"# Evidence Matrix (project {matrix.get('project_id')})",
        "",
        f"_matrix_version {matrix.get('matrix_version')} · "
        f"{(matrix.get('metrics') or {}).get('paper_count', 0)} papers · "
        f"coverage {(matrix.get('metrics') or {}).get('coverage')}_",
        "",
        "| Paper | Method | Dataset | Findings | Limitations |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in matrix.get("rows") or []:
        paper = row.get("paper_title") or f"#{row.get('file_id')}"
        year = row.get("paper_year") or ""
        if year:
            paper = f"{paper} ({year})"

        def cell(key: str) -> str:
            c = row.get(key) or {}
            if c.get("status") == "unknown" or not c.get("value"):
                return "_unknown_"
            val = str(c["value"]).replace("|", "\\|").replace("\n", " ")
            ids = c.get("evidence_ids") or []
            cite = f" [e:{','.join(str(i) for i in ids[:5])}]" if ids else ""
            return f"{val}{cite}"

        lines.append(
            f"| {paper.replace('|', '\\|')} | {cell('method')} | {cell('dataset')} | "
            f"{cell('findings')} | {cell('limitations')} |"
        )
    lines.append("")
    return "\n".join(lines)


def matrix_to_csv(matrix: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "file_id",
            "paper_title",
            "paper_year",
            "method",
            "method_evidence_ids",
            "method_status",
            "dataset",
            "dataset_evidence_ids",
            "dataset_status",
            "findings",
            "findings_evidence_ids",
            "findings_status",
            "limitations",
            "limitations_evidence_ids",
            "limitations_status",
            "evidence_count",
        ]
    )
    for row in matrix.get("rows") or []:

        def ids(key: str) -> str:
            return ",".join(str(i) for i in ((row.get(key) or {}).get("evidence_ids") or []))

        def val(key: str) -> str:
            c = row.get(key) or {}
            if c.get("status") == "unknown":
                return "unknown"
            return str(c.get("value") or "unknown")

        def st(key: str) -> str:
            return str((row.get(key) or {}).get("status") or "unknown")

        writer.writerow(
            [
                row.get("file_id"),
                row.get("paper_title"),
                row.get("paper_year"),
                val("method"),
                ids("method"),
                st("method"),
                val("dataset"),
                ids("dataset"),
                st("dataset"),
                val("findings"),
                ids("findings"),
                st("findings"),
                val("limitations"),
                ids("limitations"),
                st("limitations"),
                row.get("evidence_count"),
            ]
        )
    return buf.getvalue()
