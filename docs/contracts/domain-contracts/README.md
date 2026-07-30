# Domain Contracts (living)

**Owner:** Developer A  
**Parent:** [IDD-0002](../../idd/IDD-0002-Domain-Model.md)  
**contracts_version:** 1.0.0  

## Purpose

Canonical entity names and lifecycle enums. Implementation tables may use legacy names (`files`); **domain language** in APIs/docs uses the names below.

## Frozen entities

| Domain name | Persistence (v1) | Notes |
|-------------|------------------|-------|
| User | `users` | |
| Project | `projects` | |
| Library | view over Papers | Not a root table |
| Paper | `files` | **No** `papers` table |
| Author | metadata / AuthorRef | |
| Section / Figure / Table / Reference | DU payloads or future child tables | Non-blocking |
| EvidenceObject | `evidence_objects` | Canonical knowledge unit |
| Claim | field/view of EvidenceObject | **Not** a root table |
| Annotation | notes or future table | |
| WritingDocument | `documents` | |
| WritingSection | logical sections | |
| Citation | `writing_sentence_bindings` | |
| ReviewerFinding | review DTO / future `reviewer_runs` | ≠ claim_reviews |
| SearchResult | response DTO | |
| ExportJob | job or sync export | |

## Frozen enums

See IDD-0002 §4 — especially:

- Evidence status: `candidate` \| `accepted` \| `rejected` \| `superseded`
- Confidence: `low` \| `moderate` \| `high`
- EvidenceQuery intents & writing `section_type`s
- Reviewer severities: `info` \| `warning` \| `error`

## Single source of truth rule

Do not introduce a second root for Paper or Claim without ADR reversing ADR-0003.
