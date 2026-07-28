"""Week 1.1 sustained load / stress checks for Writing Studio Shell.

Stage 4 smoke budgets remain in test_writing_performance.py.
These tests exercise longer sequences and report percentile latency.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import statistics
import time
from pathlib import Path

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server

REPORT_PATH = Path("docs/architecture/week1.1-sustained-load-report.md")


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _seed_doc(user_id: int):
    db = server.SessionLocal()
    try:
        user = server.User(
            id=user_id,
            email=f"sustained{user_id}@example.com",
            name=f"Sustained {user_id}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        project = server.Project(user_id=user_id, name=f"Project {user_id}", emoji="P")
        db.add(project)
        db.flush()
        doc = server.WritingDocument(
            user_id=user_id,
            project_id=project.id,
            title="Sustained Draft",
            content="hello world",
            status="active",
            current_version=1,
            last_saved_hash="seed-hash",
        )
        db.add(doc)
        db.commit()
        return {"project_id": project.id, "document_id": doc.id}
    finally:
        db.close()


def _ms(fn):
    started = time.perf_counter()
    response = fn()
    return response, (time.perf_counter() - started) * 1000


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _summary(latencies_ms: list[float]) -> dict:
    ordered = sorted(latencies_ms)
    return {
        "n": len(ordered),
        "p50_ms": round(_percentile(ordered, 50), 2),
        "p95_ms": round(_percentile(ordered, 95), 2),
        "max_ms": round(max(ordered), 2) if ordered else 0.0,
        "mean_ms": round(statistics.fmean(ordered), 2) if ordered else 0.0,
        "error_count": 0,
    }


def test_burst_autosave_sustained_latency():
    """40 sequential content-changing autosaves — burst profile."""
    seeded = _seed_doc(4101)
    client = _client()
    _login(client, 4101)
    latencies: list[float] = []
    errors = 0
    version = 1

    for i in range(40):
        resp, elapsed = _ms(
            lambda i=i, version=version: client.post(
                f"/api/writing/documents/{seeded['document_id']}/autosave",
                json={
                    "title": "Sustained Draft",
                    "content": f"burst content {i}",
                    "current_version": version,
                    "idempotency_key": f"burst-{i}",
                },
            )
        )
        latencies.append(elapsed)
        if resp.status_code != 200:
            errors += 1
            continue
        body = resp.get_json() or {}
        doc = body.get("document") or {}
        version = int(doc.get("current_version") or version)

    stats = _summary(latencies)
    stats["error_count"] = errors
    assert errors == 0
    # Sustained gate: looser than single-shot smoke but still bounded.
    assert stats["p95_ms"] < 1500, stats
    assert stats["max_ms"] < 3000, stats

    _append_report_section(
        "Burst autosave (n=40)",
        stats,
        notes="Sequential content-changing autosaves on one document; version advanced each save.",
    )


def test_cohort_list_open_autosave_cycle():
    """Baseline cohort: list → open → autosave repeated."""
    seeded = _seed_doc(4102)
    client = _client()
    _login(client, 4102)

    list_ms: list[float] = []
    open_ms: list[float] = []
    save_ms: list[float] = []
    errors = 0
    version = 1

    for i in range(25):
        list_resp, list_elapsed = _ms(
            lambda: client.get(
                f"/api/writing/documents?project_id={seeded['project_id']}&status=active"
            )
        )
        open_resp, open_elapsed = _ms(
            lambda: client.get(f"/api/writing/documents/{seeded['document_id']}")
        )
        save_resp, save_elapsed = _ms(
            lambda i=i, version=version: client.post(
                f"/api/writing/documents/{seeded['document_id']}/autosave",
                json={
                    "title": "Sustained Draft",
                    "content": f"cohort cycle {i}",
                    "current_version": version,
                    "idempotency_key": f"cohort-{i}",
                },
            )
        )
        list_ms.append(list_elapsed)
        open_ms.append(open_elapsed)
        save_ms.append(save_elapsed)
        if list_resp.status_code != 200 or open_resp.status_code != 200 or save_resp.status_code != 200:
            errors += 1
            continue
        body = save_resp.get_json() or {}
        doc = body.get("document") or {}
        version = int(doc.get("current_version") or version)

    assert errors == 0
    list_stats = _summary(list_ms)
    open_stats = _summary(open_ms)
    save_stats = _summary(save_ms)
    assert list_stats["p95_ms"] < 1500, list_stats
    assert open_stats["p95_ms"] < 1500, open_stats
    assert save_stats["p95_ms"] < 1500, save_stats

    _append_report_section("Cohort list p95", list_stats, notes="25× list documents")
    _append_report_section("Cohort open p95", open_stats, notes="25× open document")
    _append_report_section("Cohort autosave p95", save_stats, notes="25× autosave after list/open")


def test_conflict_storm_stale_version_rate():
    """Concurrent-edit simulation: many stale version attempts after one advance."""
    seeded = _seed_doc(4103)
    client = _client()
    _login(client, 4103)

    first = client.post(
        f"/api/writing/documents/{seeded['document_id']}/autosave",
        json={
            "title": "Sustained Draft",
            "content": "advance once",
            "current_version": 1,
            "idempotency_key": "conflict-advance",
        },
    )
    assert first.status_code == 200, first.get_json()

    conflict_ms: list[float] = []
    conflict_count = 0
    for i in range(20):
        resp, elapsed = _ms(
            lambda i=i: client.patch(
                f"/api/writing/documents/{seeded['document_id']}",
                json={"content": f"stale {i}", "current_version": 1},
            )
        )
        conflict_ms.append(elapsed)
        if resp.status_code == 409:
            conflict_count += 1
        else:
            assert resp.status_code == 409, resp.get_json()

    stats = _summary(conflict_ms)
    stats["conflict_count"] = conflict_count
    assert conflict_count == 20
    assert stats["p95_ms"] < 1500, stats
    _append_report_section(
        "Conflict storm (stale version ×20)",
        stats,
        notes="All requests must return 409 version_conflict after head advances.",
    )


_REPORT_SECTIONS: list[dict] = []


def _append_report_section(title: str, stats: dict, *, notes: str) -> None:
    _REPORT_SECTIONS.append({"title": title, "stats": stats, "notes": notes})


def test_write_sustained_load_report(tmp_path=None):
    """Finalize markdown report after other tests in this module have run.

    Pytest collects tests in definition order within a file when not otherwise
    ordered; this test only asserts the report can be written from accumulated
    sections if present, and always writes a timestamped scaffold.
    """
    # Ensure this module's load tests have populated sections when run as a file.
    # If run in isolation, still emit a stub report for the evidence pack.
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Week 1.1 Sustained Load Report",
        "",
        f"Generated: `{now}`",
        "Scope: Writing Studio Shell API (`/api/writing/documents*`)",
        "Environment: Flask test client (local SQLite via root conftest)",
        "",
        "## Budgets",
        "",
        "- Stage 4 smoke (single-shot): < 500ms (see `tests/test_writing_performance.py`)",
        "- Week 1.1 sustained p95: < 1500ms per operation class",
        "- Week 1.1 sustained max: < 3000ms",
        "",
        "## Results",
        "",
    ]
    if _REPORT_SECTIONS:
        for section in _REPORT_SECTIONS:
            lines.append(f"### {section['title']}")
            lines.append("")
            lines.append(f"- Notes: {section['notes']}")
            lines.append(f"- Stats: `{json.dumps(section['stats'], sort_keys=True)}`")
            lines.append("")
    else:
        lines.append("_No in-process sections captured (run full module to populate)._")
        lines.append("")

    lines.extend(
        [
            "## Bottleneck notes",
            "",
            "- Measurements are process-local Flask test-client latencies, not production network RTT.",
            "- Rate limit on autosave is `120/hour` — burst profile sized under that ceiling.",
            "- Remediation priority if p95 breaches: document open query path, autosave version row insert, activity logging.",
            "",
            "## Gate",
            "",
            "- [x] Sustained suite present (`tests/test_writing_sustained_load.py`)",
            "- [x] Report artifact path reserved for Week 1.1 evidence pack",
            "",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert REPORT_PATH.exists()
