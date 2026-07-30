# A-402 — Evidence Object & RI Payload Contract

**Status:** Frozen (A-402 + A-403 additives)  
**contracts_version:** `1.2.0`  
**Source of truth (code):** `backend/evidence/objects.py` · `envelope.py` · stage modules · `writing/reviewer_persistence.py`  
**Parent:** [IDD-0002](../idd/IDD-0002-Domain-Model.md) · [api-contracts.md](./api-contracts.md)

---

## 1. EvidenceObject DTO (frozen)

Returned by list/get/review/explain/`objects[]` on RI routes.

| Field | Type | Null? | Notes |
|-------|------|-------|--------|
| `id` | int | no* | |
| `user_id` | int | no* | |
| `project_id` | int | no* | |
| `file_id` | int | no* | Paper storage id |
| `paper_id` | int | no* | **Alias of `file_id`** (dual-read) |
| `page` | int \| null | yes | Single page anchor (not `page_start`/`page_end`) |
| `char_start` | int \| null | yes | Offset/span start |
| `char_end` | int \| null | yes | Offset/span end |
| `section` | string | no | May be `""` |
| `quote` | string | no | Source excerpt |
| `claim` | string | no | Normalized claim |
| `study_type` | string | no | May be `""` |
| `study_quality` | string | no | May be `""` |
| `supports` | string[] | no | |
| `contradicts` | string[] | no | |
| `limitations` | string[] | no | |
| `confidence_band` | string | no | `low` \| `moderate` \| `high` |
| `status` | string | no | `candidate` \| `accepted` \| `rejected` \| `superseded` |
| `pipeline_version` | string | no | Extract pipeline semver |
| `created_by` | string | no | |
| `content_hash` | string | no | Idempotency / identity |
| `supersedes_id` | int \| null | yes | Edit chain |
| `provenance` | object | no | Opaque JSON object (`{}` if empty) |
| `source_kg_node_id` | string | no | May be `""` |
| `created_at` | string \| null | yes | ISO-8601 |
| `updated_at` | string \| null | yes | ISO-8601 |

\*Present on normal rows; serializers use `getattr` defaults for safety.

### Additive optional fields (non-breaking when present)

| Field | When |
|-------|------|
| `relation` | Explain / binding context (`supports` \| `contradicts` \| `related`) |
| `file_title` | When serializer is given a title |

### Not in v1 DTO (do not depend on)

`finding`, `evidence_type`, `page_start`, `page_end` — IDD aspirational names; **not emitted**.

### Provenance

`provenance` is an open object. Clients may read known keys if present but **MUST tolerate** unknown keys and empty `{}`. Changing required provenance keys is a **minor** bump only if additive; removing/renaming is **breaking**.

---

## 2. Confidence & status enums (frozen)

```text
confidence_band:  low | moderate | high
status:           candidate | accepted | rejected | superseded
relation:         supports | contradicts | related
```

Meaning of status transitions is owned by human review + extract — do not redefine without ADR.

---

## 3. Citation payload (writing) (frozen)

Items in `writing.citations[]` and bibliography entries:

| Field | Required | Notes |
|-------|----------|--------|
| `evidence_id` | yes | EvidenceObject id |
| `file_id` | yes when known | |
| `page` | nullable | |
| `claim` | string | |
| `quote` | string | |
| `confidence_band` | optional | |
| `study_type` | optional | |

**Do not** send/expect `evidence_object_id` on writing citations (legacy IDD sketch).

---

## 4. Stage payloads (frozen keys)

### consensus

`label`, `supporting`, `contradicting`, `neutral`, `supporting_ids`, `contradicting_ids`, `neutral_ids`

**Additive (A-403):** `metrics` object with `support_ratio`, `contested_ratio`, `agreement_score`, `weighted_supporting`, `weighted_contradicting`, `weighted_support_ratio`, `polar_count` (and echoed `neutral`). Clients may ignore.

**Additive (RI-003):** `product_label` — researcher-facing stance: `Agree` | `Disagree` | `Mixed` | `Weak evidence`. Ordinal `label` (`strong`/`moderate`/`contested`/`opposed`/`none`) remains unchanged for machine consumers. Stage version `consensus_version: "1.2.0"`.

### conflict

`has_conflict`, `mediators`, `links[]` (`a_id`, `b_id`, `a_stance`, `b_stance`, `mediators`), `pair_count`, `supporting_ids`, `contradicting_ids`

Mediator catalog (append-only): `population_differs`, `dosage_differs`, `method_differs`, `outcome_differs`, `timeframe_differs` (A-403), `statistics_differs` (RI-004).

**Additive (A-403):** `metrics` with `mediated_pair_count`, `unexplained_pair_count`, `mediation_coverage`.

**Additive (RI-004):** per-link `why[]` (`code`, `title`, `why`, optional `supporting_signals` / `contradicting_signals`), `facet_detail`, `unexplained`; top-level `mediator_explanations[]` and `product_summary`. Stage version `conflict_version: "1.2.0"`.

### matrix (RI-002)

Project-scoped derived view (not an EvidenceQuery stage).  
`GET /api/projects/{project_id}/evidence/matrix`

JSON keys: `stage: "matrix"`, `matrix_version` (`"1.0.0"`), `project_id`, `columns` (`paper`, `method`, `dataset`, `findings`, `limitations`), `rows[]`, `metrics`.

Each row: `file_id`, `paper_title`, `paper_year`, `paper_authors`, `evidence_count`, plus cells `method` / `dataset` / `findings` / `limitations` shaped as:

```text
{ value: string|null, status: "known"|"unknown", evidence_ids: int[], sources: string[] }
```

Cell fill order: EvidenceObject fields first (`study_type`, provenance.dataset, `claim`/`supports`, `limitations[]`); then optional PaperAnalysis fallback (`methodology`, `dataset`, `results`/`key_contributions`, `limitations`). Empty → `status: "unknown"` (never invent).

Query: `format=json|markdown|csv` (default json); `file_ids` comma list; `status` filter (default `candidate,accepted`).

### themes (RI-001)

Project-scoped derived view.  
`GET /api/projects/{project_id}/evidence/themes`

JSON keys: `stage: "themes"`, `themes_version` (`"1.0.0"`), `project_id`, `run` (`algorithm`, `params`, `input_hash`, `object_count`, `generated_at`), `themes[]`, `unassigned`, `metrics`.

Each theme: `id` (`theme_a`…), `letter`, `label` (`Theme A — …`), `key_terms`, `evidence_ids`, `file_ids`, `size`, `sample_claims`, `study_types`.

Algorithm `token_jaccard_v1` — deterministic greedy Jaccard clustering over claim/quote tokens. Never invents evidence ids. Same inputs + params → same `input_hash` membership (reconstructable).

Query: `format=json|markdown`; `file_ids`; `status`; `similarity_threshold` (0.05–0.95, default 0.22); `min_cluster_size` (1–20, default 2); `max_themes` (1–40, default 12).

### gaps (RI-006)

`GET /api/projects/{project_id}/evidence/gaps`

JSON: `stage: "gaps"`, `gaps_version` (`"1.0.0"`), `project_id`, `run`, `gaps[]`, `metrics`.

Gap types (append-only): `thin_theme`, `missing_matrix_cell`, `weak_consensus`, `unexplained_conflict`, `coverage`.

Each gap: `id`, `type`, `statement`, `evidence_density`, `suggested_questions[]`, `evidence_ids[]` (+ optional `theme_id`, `file_ids`, `matrix`, `conflict_link`). Templated from themes/matrix/consensus/conflict — never invents literature.

### graph (RI-005)

`GET /api/projects/{project_id}/evidence/graph`

JSON: `stage: "graph"`, `graph_version` (`"1.0.0"`), `project_id`, `run`, `nodes[]`, `edges[]`, `metrics`.

Node types: `paper`, `evidence`, `theme`. Edge types: `from`, `in_theme`, `contradicts`, `related`. Project-level over EvidenceObjects (+ themes); optional conflict links. No Neo4j / parallel graph DB.

### timeline (RI-007)

`GET /api/projects/{project_id}/evidence/timeline`

JSON: `stage: "timeline"`, `timeline_version` (`"1.0.0"`), `span`, `entries[]` (year buckets with `file_ids`, `evidence_ids`, `theme_ids`/`theme_labels`, `sample_claims`), `undated`, `evolution` (theme first/last year), `metrics`.

Year resolution: paper metadata → provenance → claim/quote text. Never invents papers.

### methodology (RI-008)

`GET /api/projects/{project_id}/evidence/methodology`

JSON: `stage: "methodology"`, `methodology_version` (`"1.0.0"`), `cards[]`, `design_summary`, `disclaimer`, `metrics`.

Card kinds: `study_design`, `dataset`, `variables`, `statistics`, `threats_to_validity`. All `tone: "advisory"` — supportive guidance grounded in Evidence/matrix/gaps; never invents literature or commands new studies.

### ranking diagnostics (additive)

Optional on ranking (+ forwarded) stages: `ranking_diagnostics: { strategy, ranking_version, object_scores: { "<id>": { factors, composite? } } }`. Never mutates EvidenceObject DTOs.

### reasoning

`summary_code`, `sufficiency`, `steps[]`, `evidence_ids`, `mediator_labels`

### writing

See [api-contracts.md](./api-contracts.md) §8. Nested under RI envelope key `writing`.

**RI-009:** `writing_version` `2.0.0` / `mode` `grounded_v1` + additive `ri_context` (themes from RI-001, gaps from RI-006, consensus/conflict echoes). Section drafts consume RI depth; citations still only from EvidenceObjects.

### review (ReviewerResult inside writing)

| Field | Notes |
|-------|--------|
| `reviewer_version` | e.g. `"1.1.0"` |
| `name` | e.g. `research_reviewer` |
| `status` | `pass` \| `fail` (product) |
| `pass_rate` | float |
| `sections_checked` / `sections_passed` | int |
| `issue_count` | int |
| `issues[]` | `{ code, severity, section_id?, message, evidence_ids? }` |
| `metrics` | object (grounding / coverage fields may grow additively) |

Severities: `info` \| `warning` \| `error`.

---

## 5. ReviewerRun / ReviewerFinding (frozen)

Distinct from **ClaimReview** (`POST …/reviews` on EvidenceObject).

### ReviewerRun

`id`, `user_id`, `project_id`, `document_id`, `document_version_no`, `writing_version`, `reviewer_version`, `binder_version`, `status`, `pass_rate`, `sections_checked`, `sections_passed`, `issue_count`, `metrics`, `input_snapshot`, `model_version_id` (nullable), `prompt_version_id` (nullable), `prompt_meta`, `created_at`, `finished_at`

When loaded fully: `findings[]`, reconstructed `review`.

### ReviewerFinding

`id`, `run_id`, `code`, `severity`, `message`, `section_id`, `block_id`, `range_start`, `range_end`, `selected_text`, `evidence_ids`, `confidence_band`, `recommendation`, `status`, `resolution_rationale`, `resolved_at`, `resolved_by`, `created_at`

Resolution fields are reserved for future UI; treat as optional.

### input_snapshot

Compact historical context: `sections[]` (ids, hashes, previews, evidence_ids), `evidence_ids`, consensus/conflict labels — so later EvidenceObject edits do not rewrite history.

---

## 6. Explain DTO (frozen surface)

| Field | Notes |
|-------|--------|
| `status` | `"ok"` |
| `sufficiency` | product enum/string |
| `sentence` | `{ block_id, range_start, range_end, text }` |
| `evidence` | EvidenceObject[] (+ optional `relation`) |
| `chain` | explainability steps |
| `warnings` | string[] |

---

## 7. Compatibility commitments

1. **Evidence IDs are stable integers** within a deployment; clients may store them in bindings and citations.  
2. **Dual-read `file_id` / `paper_id`** remains for v1. New fields should prefer documenting `file_id` in APIs and `Paper` in domain prose.  
3. Additive optional fields are allowed without version bump of the **path**; bump `contracts_version` minor.  
4. Removing or renaming any table in §1–§5 is **breaking**.
