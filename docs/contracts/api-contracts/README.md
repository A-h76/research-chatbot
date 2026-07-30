# API Contracts (living)

**Owner:** Developer A  
**Parent:** [IDD-0003](../../idd/IDD-0003-API-Contracts.md)  
**contracts_version:** 1.0.0  

## Purpose

Day-to-day reference for route names, methods, auth, and DTO names. Full examples and status tables live in IDD-0003; **this file is the freeze index**.

## Frozen route index (v1)

| Method | Route | Auth | Primary DTO |
|--------|-------|------|-------------|
| GET | `/api/me` | Session/JWT | `User` |
| GET | `/api/auth/jwt` | Session | `{ access, expires_in }` |
| GET/POST/PATCH | `/api/projects`… | Session | `Project` |
| GET/POST/DELETE | `/api/files`… | Session | `Paper` (alias file) |
| POST | `/api/documents/upload` | JWT | `Paper` + job |
| GET | `/api/library/connections` | Session | Connection status |
| GET | `/api/projects/{id}/evidence` | Session | `EvidenceObject[]` |
| GET | `/api/evidence/{id}` | Session | `EvidenceObject` |
| POST | `/api/projects/{id}/evidence/extract` | Session | Job accepted |
| POST | `/api/evidence/{id}/reviews` | Session | `EvidenceObject` |
| POST | `/api/evidence/explain` | Session | Explain DTO (ADR-frozen) |
| POST | `/api/evidence/search` \| `retrieve` | Session | Evidence list |
| POST | `/api/evidence/rank` | Session | Ranked list |
| POST | `/api/evidence/consensus` | Session | Aggregate |
| POST | `/api/evidence/conflict` | Session | Mediators |
| POST | `/api/evidence/reason` | Session | Reasoning |
| POST | `/api/evidence/writing` | Session | `GroundedWritingResult` |
| CRUD | `/api/writing/documents`… | Session | `WritingDocument` |
| POST/DELETE | evidence-bindings | Session | `CitationBinding` |
| POST | `/api/search` | Session | `SearchResult[]` |

## Frozen rules

1. EvidenceQuery **must not** include `prompt`, `model`, `temperature`, `embeddings`, `provider`, `api_key`.
2. Error body: `{ error, detail?, fields? }`.
3. Additive response fields only without ADR.
4. `file_id` / `paper_id` dual naming allowed in v1; new clients prefer `paper_id` in docs, send `file_id` where legacy requires.

## Change process

ADR → update IDD-0003 → update this index → bump `contracts_version` → notify Developer B.
