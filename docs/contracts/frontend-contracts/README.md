# Frontend Contracts (living)

**Owner:** Developer B  
**Parent:** [IDD-0004](../../idd/IDD-0004-Frontend-Contracts.md)  
**contracts_version:** 1.0.0  

## Purpose

Page data requirements + **frozen TypeScript type names** for parallel UI work. Full interface bodies live in IDD-0004 §3; keep this index + `frontend/src/types/idd.ts` in sync.

## Frozen type names

```text
User
Project
AuthorRef
Paper
EvidenceObject
EvidenceQuery
EvidenceStatus
ConfidenceBand
WritingDocument
WritingSectionType
GroundedWritingResult
ReviewerFinding
CitationBinding
SearchResult
JobStatus
ExportJob
ApiErrorBody
Paginated<T>
```

## Page contract index

| Route | Required APIs (summary) | Critical states |
|-------|-------------------------|-----------------|
| `/home` | me, summary counts | empty → CTA library |
| `/` projects | projects CRUD | empty → create |
| `/library` | files list, upload, connections | empty CTAs per vision |
| `/papers/:id` | paper, pipeline, extract | not-ready stages |
| `/writing` | documents, evidence/writing, bindings | blocked ≠ transport error |
| Inspector | evidence get, explain, reviews | citation → panel |
| `/search` | search, discover | no “Thinking…” |
| `/research/compare` | compare/gaps (+ RI later) | select ≥2 papers |

## Client rules

1. Depend only on published API + these types.  
2. Ignore unknown JSON fields.  
3. Use `apiClient` / JWT helper—no ad-hoc auth.  
4. Optimistic updates only where IDD-0004 allows; rollback on failure.

## Change process

ADR (if frozen) → IDD-0004 → this README → update `frontend/src/types/idd.ts` → bump `contracts_version`.
