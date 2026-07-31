"""W5 — Structured extraction tables (PICO / methods / outcomes).

Builds typed rows from Phase-1 ``medical_understanding`` (never invents
fields). Optional EvidenceObject locators enrich source cites.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Optional

EXTRACT_TABLE_VERSION = "1.0.0"
COLUMNS = (
    "population",
    "intervention",
    "comparator",
    "outcomes",
    "study_design",
    "methods",
    "key_findings",
)


def _trim(text: str, limit: int = 500) -> str:
    t = " ".join((text or "").strip().split())
    if len(t) <= limit:
        return t
    return t[: limit - 1].rstrip() + "…"


def _join_names(items: Any, *, name_keys: tuple[str, ...] = ("name", "description", "value")) -> str:
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for it in items:
        if isinstance(it, str) and it.strip():
            parts.append(it.strip())
            continue
        if not isinstance(it, dict):
            continue
        for k in name_keys:
            v = it.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
                break
    return _trim("; ".join(dict.fromkeys(parts)))


def _cell(value: str | None, *, sources: list[str] | None = None) -> dict[str, Any]:
    text = _trim(value or "")
    if not text:
        return {"value": None, "status": "unknown", "sources": []}
    return {
        "value": text,
        "status": "known",
        "sources": list(dict.fromkeys(sources or [])),
    }


def _methods_summary(study: dict[str, Any] | None) -> str:
    if not isinstance(study, dict):
        return ""
    parts: list[str] = []
    design = study.get("study_design")
    if isinstance(design, str) and design.strip():
        parts.append(design.strip())
    arms = study.get("number_of_arms")
    if arms is not None:
        parts.append(f"{arms} arms")
    blinding = study.get("blinding")
    if isinstance(blinding, str) and blinding.strip():
        parts.append(blinding.strip())
    if study.get("multicenter") is True:
        parts.append("multicenter")
    return _trim("; ".join(parts))


def row_from_medical_understanding(
    *,
    file_id: int,
    paper_title: str,
    paper_year: str = "",
    medical: dict[str, Any] | None,
    evidence_objects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """One structured-extract row for a paper."""
    mu = medical if isinstance(medical, dict) else {}
    skipped = bool(mu.get("skipped"))
    study = mu.get("study_characteristics") if isinstance(mu.get("study_characteristics"), dict) else {}

    pop = _join_names(mu.get("populations"), name_keys=("description", "name", "value"))
    if not pop:
        pico = mu.get("pico_elements") if isinstance(mu.get("pico_elements"), dict) else {}
        p = pico.get("population")
        if isinstance(p, dict):
            pop = _trim(str(p.get("description") or ""))

    intervention = _join_names(mu.get("interventions"))
    comparator = _join_names(mu.get("comparators"))
    outcomes = _join_names(mu.get("outcomes"))
    findings = _join_names(mu.get("key_findings"), name_keys=("statement", "name", "value"))
    design = ""
    if isinstance(study.get("study_design"), str):
        design = study["study_design"].strip()
    methods = _methods_summary(study)

    # Locators from evidence objects (page-anchored claims) when present.
    sources: list[str] = []
    for o in evidence_objects or []:
        page = o.get("page")
        claim = o.get("claim") or o.get("quote") or ""
        if page is not None and claim:
            sources.append(f"p.{page}")
        elif page is not None:
            sources.append(f"p.{page}")
        if len(sources) >= 6:
            break

    status = "empty" if skipped or not mu else "ok"
    known = sum(
        1
        for v in (pop, intervention, comparator, outcomes, design, methods, findings)
        if v
    )
    if known == 0 and status == "ok":
        status = "empty"

    return {
        "file_id": int(file_id),
        "paper_title": paper_title or f"#{file_id}",
        "paper_year": paper_year or "",
        "status": status,
        "population": _cell(pop, sources=sources[:2] if pop else None),
        "intervention": _cell(intervention),
        "comparator": _cell(comparator),
        "outcomes": _cell(outcomes),
        "study_design": _cell(design),
        "methods": _cell(methods),
        "key_findings": _cell(findings, sources=sources[:3] if findings else None),
        "has_medical_understanding": bool(mu) and not skipped,
        "evidence_count": len(evidence_objects or []),
    }


def build_structured_extract_table(
    *,
    project_id: Optional[int],
    papers: list[dict[str, Any]],
) -> dict[str, Any]:
    """``papers`` items: file_id, paper_title, paper_year?, medical?, evidence_objects?."""
    rows = [
        row_from_medical_understanding(
            file_id=int(p["file_id"]),
            paper_title=str(p.get("paper_title") or ""),
            paper_year=str(p.get("paper_year") or ""),
            medical=p.get("medical"),
            evidence_objects=p.get("evidence_objects") or [],
        )
        for p in papers
    ]
    filled = sum(1 for r in rows if r["status"] == "ok")
    return {
        "stage": "structured_extract",
        "extract_version": EXTRACT_TABLE_VERSION,
        "project_id": project_id,
        "columns": list(COLUMNS),
        "rows": rows,
        "metrics": {
            "paper_count": len(rows),
            "filled_rows": filled,
            "empty_rows": len(rows) - filled,
            "coverage": round(filled / len(rows), 3) if rows else 0.0,
        },
    }


def table_to_markdown(table: dict[str, Any]) -> str:
    lines = [
        f"# Structured extract (project {table.get('project_id')})",
        "",
        f"_extract_version {table.get('extract_version')} · "
        f"{(table.get('metrics') or {}).get('paper_count', 0)} papers · "
        f"coverage {(table.get('metrics') or {}).get('coverage')}_",
        "",
        "| Paper | Population | Intervention | Comparator | Outcomes | Design | Methods | Key findings |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    def cell(row: dict[str, Any], key: str) -> str:
        c = row.get(key) or {}
        if c.get("status") == "unknown" or not c.get("value"):
            return "_unknown_"
        return str(c["value"]).replace("|", "\\|").replace("\n", " ")

    for row in table.get("rows") or []:
        paper = row.get("paper_title") or f"#{row.get('file_id')}"
        year = row.get("paper_year") or ""
        if year:
            paper = f"{paper} ({year})"
        lines.append(
            f"| {str(paper).replace('|', '\\|')} | {cell(row, 'population')} | "
            f"{cell(row, 'intervention')} | {cell(row, 'comparator')} | "
            f"{cell(row, 'outcomes')} | {cell(row, 'study_design')} | "
            f"{cell(row, 'methods')} | {cell(row, 'key_findings')} |"
        )
    lines.append("")
    return "\n".join(lines)


def table_to_csv(table: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "file_id",
            "paper_title",
            "paper_year",
            "population",
            "intervention",
            "comparator",
            "outcomes",
            "study_design",
            "methods",
            "key_findings",
            "status",
        ]
    )
    for row in table.get("rows") or []:

        def val(key: str) -> str:
            c = row.get(key) or {}
            if c.get("status") == "unknown":
                return "unknown"
            return str(c.get("value") or "unknown")

        writer.writerow(
            [
                row.get("file_id"),
                row.get("paper_title"),
                row.get("paper_year"),
                val("population"),
                val("intervention"),
                val("comparator"),
                val("outcomes"),
                val("study_design"),
                val("methods"),
                val("key_findings"),
                row.get("status"),
            ]
        )
    return buf.getvalue()


def table_prompt_block(table: dict[str, Any], *, max_rows: int = 12) -> str:
    """Compact markdown for chat ``extract`` skill grounding."""
    rows = (table.get("rows") or [])[:max_rows]
    if not rows:
        return ""
    slim = {
        "extract_version": table.get("extract_version"),
        "rows": [
            {
                "file_id": r.get("file_id"),
                "paper": r.get("paper_title"),
                "population": (r.get("population") or {}).get("value"),
                "intervention": (r.get("intervention") or {}).get("value"),
                "comparator": (r.get("comparator") or {}).get("value"),
                "outcomes": (r.get("outcomes") or {}).get("value"),
                "study_design": (r.get("study_design") or {}).get("value"),
                "methods": (r.get("methods") or {}).get("value"),
                "key_findings": (r.get("key_findings") or {}).get("value"),
            }
            for r in rows
            if r.get("status") == "ok"
        ],
    }
    if not slim["rows"]:
        return ""
    return (
        "Structured extract table (from document understanding — prefer these "
        "fields over inventing PICO/methods). Fill 'Not in excerpts' only when "
        "a field is null here AND absent from passages.\n"
        + json.dumps(slim, ensure_ascii=False)
    )
