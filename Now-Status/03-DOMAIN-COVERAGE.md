# 03 — Domain Coverage vs Research OS Vision

Legend: ✅ Implemented · 🟡 Partial · ❌ Missing  

Vision sources: `docs/UI_UX_VISION_BETA_v1.0.md`, ADRs 0001–0007, Phase 2 writing roadmap, constitution Principle 11.

| Domain | Status | Evidence in codebase | Gap |
|--------|--------|----------------------|-----|
| **Projects** | ✅ | `projects`, hub APIs, questions, research console, instructions | Multi-user / teams later |
| **Library** | ✅ | `files` as paper identity, collections, Zotero/Mendeley, readiness | Naming (`files` vs Library); dual upload |
| **Document Understanding** | ✅ | Phase 1.1 + importers + chunks/embeddings | Version stamps on all analysis rows incomplete |
| **Evidence Layer** | ✅ | Tables + extract + review + explain + bindings (ADR-0003/0005) | Inspector polish; docs lag |
| **Writing** | 🟡 | Shell + grounded `/api/evidence/writing` + UI desk | Not all section types battle-tested; classic transform still parallel |
| **Reviewer** | 🟢 | Durable `reviewer_runs` / `reviewer_findings` + GET reconstruct APIs (A-401) | FE accordion / export gate still open (EPIC-0005 B-*) |
| **Ranking** | 🟢 | Strategy registry + `ranking_diagnostics` (A-403) | Product UI strategy picker optional |
| **Consensus** | 🟢 | API + additive `metrics` (A-403) | Product Compare UI thin |
| **Knowledge Graph** | 🟡 | Phase 1.7 per-document; UI paper graph tab | No project-level research graph product |
| **Research Assistant** | 🟡 | Project research presets + Ask-from-library + chat | Correctly demoted; not Evidence-first everywhere |
| **Export** | 🟡 | Markdown/export snapshot from grounded writing | Journal toolkit / DOCX / BibTeX packs incomplete |
| **Authentication** | ✅ | Google, magic link, JWT, closed beta, password ops | — |
| **Search** | 🟡 | Library semantic search + OpenAlex discover | Dual endpoints; SearchIndex unused |
| **Retrieval** | 🟡 | Chunk RAG + Evidence retrieve stage | No pgvector; scale limit |
| **Jobs** | 🟢 | Status + lifecycle/retry/timings (A-404) | Fine-grained progress still binary |

---

## Product promise alignment

| Promise | Coverage |
|---------|----------|
| Evidence first, then write | ✅ / 🟡 — enforced in EvidenceQuery + grounded writing; classic chat can still bypass |
| Human-controlled workflow | ✅ — accept/reject evidence; reviewer issues surfaced |
| Not ChatGPT-with-PDFs | 🟡 — architecture yes; some surfaces still chat-shaped |
| Trustworthy export | 🟡 — bindings + confidence; durable audit missing |

---

## Explicit non-goals (do not score as missing failures)

- Primary Chat product surface  
- Fake KG chrome without EvidenceObjects  
- Celery rewrite  
- Parallel `papers` or Claim root tables  
- Teams / JazzCash as beta blockers
