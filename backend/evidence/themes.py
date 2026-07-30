"""Theme Discovery (RI-001) — deterministic clusters over EvidenceObjects.

No LLM. No invented papers: every theme cites evidence ids from the project
corpus. Reconstructable via ``themes_version`` + ``run.input_hash`` + params.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

THEMES_VERSION = "1.0.0"
ALGORITHM = "token_jaccard_v1"

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "from",
        "by",
        "is",
        "are",
        "was",
        "were",
        "that",
        "this",
        "these",
        "those",
        "as",
        "at",
        "be",
        "been",
        "being",
        "it",
        "its",
        "into",
        "than",
        "then",
        "there",
        "their",
        "they",
        "we",
        "our",
        "vs",
        "versus",
        "not",
        "no",
        "nor",
        "but",
        "can",
        "may",
        "might",
        "will",
        "would",
        "should",
        "could",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "using",
        "used",
        "use",
        "based",
        "study",
        "studies",
        "results",
        "result",
        "effect",
        "effects",
        "among",
        "between",
        "within",
        "across",
        "also",
        "however",
        "while",
        "such",
        "more",
        "most",
        "other",
        "than",
        "over",
        "under",
        "after",
        "before",
        "during",
        "paper",
        "article",
        "authors",
        "et",
        "al",
    }
)

_LETTER_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def tokenize_claim(text: str, *, max_tokens: int = 24) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    keep = [t for t in tokens if t not in _STOP and len(t) > 2]
    return keep[:max_tokens]


def object_tokens(obj: dict[str, Any]) -> frozenset[str]:
    claim = obj.get("claim") or ""
    quote = obj.get("quote") or ""
    supports = obj.get("supports") or []
    support_text = " ".join(str(s) for s in supports) if isinstance(supports, list) else ""
    st = (obj.get("study_type") or "").strip().lower()
    base = tokenize_claim(f"{claim} {quote} {support_text}")
    if st and st not in _STOP and len(st) > 2:
        base = [st] + base
    return frozenset(base)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _letter_label(index: int) -> str:
    if index < len(_LETTER_LABELS):
        return _LETTER_LABELS[index]
    # Theme AA, AB… after Z
    q, r = divmod(index, 26)
    return f"{_LETTER_LABELS[q - 1]}{_LETTER_LABELS[r]}" if q else _LETTER_LABELS[r]


def _theme_display_name(letter: str, key_terms: list[str]) -> str:
    if key_terms:
        phrase = " ".join(key_terms[:3])
        return f"Theme {letter} — {phrase}"
    return f"Theme {letter}"


def _input_hash(objects: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for obj in sorted(objects, key=lambda o: int(o.get("id") or 0)):
        oid = obj.get("id")
        if oid is None:
            continue
        ch = obj.get("content_hash") or ""
        claim = (obj.get("claim") or "")[:200]
        parts.append(f"{int(oid)}|{ch}|{claim}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest


def discover_themes(
    objects: list[dict[str, Any]],
    *,
    project_id: int | None = None,
    similarity_threshold: float = 0.22,
    min_cluster_size: int = 2,
    max_themes: int = 12,
    max_sample_claims: int = 3,
) -> dict[str, Any]:
    """Cluster EvidenceObjects into named themes. Deterministic for fixed inputs."""
    # Stable order by id
    objs = [o for o in objects if o.get("id") is not None]
    objs.sort(key=lambda o: int(o["id"]))

    token_map: dict[int, frozenset[str]] = {}
    for o in objs:
        token_map[int(o["id"])] = object_tokens(o)

    # Greedy clustering: for each object (id order), join best matching cluster
    # if similarity >= threshold; else start a new cluster. Cluster order is
    # creation order (deterministic).
    clusters: list[list[dict[str, Any]]] = []
    cluster_tokens: list[Counter] = []

    for obj in objs:
        oid = int(obj["id"])
        toks = token_map[oid]
        best_i = -1
        best_sim = -1.0
        for i, ctoks in enumerate(cluster_tokens):
            # Represent cluster as top tokens frozenset for Jaccard
            top = frozenset(t for t, _ in ctoks.most_common(16))
            sim = jaccard(toks, top if top else frozenset())
            # Also compare to any member for denser match
            for member in clusters[i]:
                mid = int(member["id"])
                sim = max(sim, jaccard(toks, token_map[mid]))
            if sim > best_sim:
                best_sim = sim
                best_i = i
        if best_i >= 0 and best_sim >= similarity_threshold:
            clusters[best_i].append(obj)
            cluster_tokens[best_i].update(toks)
        else:
            clusters.append([obj])
            cluster_tokens.append(Counter(toks))

    # Split into themes (size >= min) vs unassigned
    sized = sorted(
        [(c, Counter(t for o in c for t in token_map[int(o["id"])])) for c in clusters],
        key=lambda pair: (-len(pair[0]), int(pair[0][0]["id"])),
    )

    themes_raw: list[tuple[list[dict[str, Any]], Counter]] = []
    unassigned: list[dict[str, Any]] = []
    for cluster, counts in sized:
        if len(cluster) >= min_cluster_size and len(themes_raw) < max_themes:
            themes_raw.append((cluster, counts))
        else:
            # Overflow beyond max_themes or small clusters
            if len(cluster) >= min_cluster_size and len(themes_raw) >= max_themes:
                # Merge overflow into unassigned (do not invent a mega-theme)
                unassigned.extend(cluster)
            else:
                unassigned.extend(cluster)

    themes: list[dict[str, Any]] = []
    for idx, (cluster, counts) in enumerate(themes_raw):
        letter = _letter_label(idx)
        key_terms = [t for t, _ in counts.most_common(5)]
        evidence_ids = [int(o["id"]) for o in cluster]
        file_ids = sorted(
            {
                int(o["file_id"])
                for o in cluster
                if o.get("file_id") is not None
            }
        )
        samples: list[dict[str, Any]] = []
        for o in cluster[:max_sample_claims]:
            samples.append(
                {
                    "evidence_id": int(o["id"]),
                    "claim": (o.get("claim") or o.get("quote") or "")[:280],
                    "file_id": o.get("file_id"),
                    "page": o.get("page"),
                }
            )
        study_types = sorted(
            {
                (o.get("study_type") or "").strip()
                for o in cluster
                if (o.get("study_type") or "").strip()
            }
        )
        themes.append(
            {
                "id": f"theme_{letter.lower()}",
                "letter": letter,
                "label": _theme_display_name(letter, key_terms),
                "key_terms": key_terms,
                "evidence_ids": evidence_ids,
                "file_ids": file_ids,
                "size": len(cluster),
                "sample_claims": samples,
                "study_types": study_types,
            }
        )

    unassigned_ids = [int(o["id"]) for o in unassigned]
    input_hash = _input_hash(objs)
    params = {
        "similarity_threshold": similarity_threshold,
        "min_cluster_size": min_cluster_size,
        "max_themes": max_themes,
        "algorithm": ALGORITHM,
    }

    return {
        "stage": "themes",
        "themes_version": THEMES_VERSION,
        "project_id": project_id,
        "run": {
            "algorithm": ALGORITHM,
            "params": params,
            "input_hash": input_hash,
            "object_count": len(objs),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "themes": themes,
        "unassigned": {
            "evidence_ids": unassigned_ids,
            "count": len(unassigned_ids),
            "reason": "below_min_cluster_size_or_over_max_themes",
        },
        "metrics": {
            "theme_count": len(themes),
            "assigned_evidence": sum(t["size"] for t in themes),
            "unassigned_evidence": len(unassigned_ids),
            "coverage": (
                round(sum(t["size"] for t in themes) / len(objs), 4) if objs else None
            ),
            "file_count": len(
                {int(o["file_id"]) for o in objs if o.get("file_id") is not None}
            ),
        },
    }


def themes_to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Theme Discovery (project {payload.get('project_id')})",
        "",
        f"_themes_version {payload.get('themes_version')} · "
        f"algorithm {(payload.get('run') or {}).get('algorithm')} · "
        f"input_hash `{(payload.get('run') or {}).get('input_hash', '')[:12]}…`_",
        "",
    ]
    for theme in payload.get("themes") or []:
        lines.append(f"## {theme.get('label')}")
        lines.append("")
        terms = ", ".join(theme.get("key_terms") or []) or "—"
        lines.append(f"- Key terms: {terms}")
        lines.append(f"- Evidence: {theme.get('size')} objects · ids {theme.get('evidence_ids')}")
        lines.append(f"- Papers (file_ids): {theme.get('file_ids')}")
        for sample in theme.get("sample_claims") or []:
            claim = (sample.get("claim") or "").replace("\n", " ")
            lines.append(f"  - [e:{sample.get('evidence_id')}] {claim}")
        lines.append("")
    un = payload.get("unassigned") or {}
    if un.get("count"):
        lines.append("## Unassigned")
        lines.append("")
        lines.append(f"- {un.get('count')} evidence objects ({un.get('reason')})")
        lines.append(f"- ids: {un.get('evidence_ids')}")
        lines.append("")
    return "\n".join(lines)


def reconstruct_fingerprint(payload: dict[str, Any]) -> str:
    """Stable fingerprint of theme membership for equality checks (ignores timestamps)."""
    themes = payload.get("themes") or []
    body = {
        "themes_version": payload.get("themes_version"),
        "input_hash": (payload.get("run") or {}).get("input_hash"),
        "params": (payload.get("run") or {}).get("params"),
        "themes": [
            {
                "id": t.get("id"),
                "evidence_ids": t.get("evidence_ids"),
                "key_terms": t.get("key_terms"),
            }
            for t in themes
        ],
        "unassigned": (payload.get("unassigned") or {}).get("evidence_ids"),
    }
    raw = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
