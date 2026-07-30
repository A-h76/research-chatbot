# Event Contracts (living)

**Owner:** Developer A  
**Parent:** [IDD-0006](../../idd/IDD-0006-Events.md)  
**contracts_version:** 1.0.0  

## Envelope (frozen)

```json
{
  "event_id": "string|number",
  "type": "PascalCasePastTense",
  "occurred_at": "ISO-8601",
  "producer": "string",
  "aggregate_type": "string",
  "aggregate_id": "string|number",
  "payload": {},
  "schema_version": 1
}
```

## Catalog (frozen names)

| Type | Aggregate | Consumers |
|------|-----------|-----------|
| `PaperUploaded` | paper | Worker, FE library |
| `PaperProcessed` | paper | FE pipeline |
| `EvidenceExtractionStarted` | run/job | FE progress |
| `EvidenceCreated` | evidence_object | FE evidence |
| `EvidenceUpdated` | evidence_object | Inspector, writing rail |
| `WritingGenerated` | document | Writing UI |
| `ReviewCompleted` | document | Reviewer UI, export — payload includes `reviewer_run_id` when persisted (A-401) |
| `ExportFinished` | export_job | Export UI |
| `BindingCreated` / `BindingDeleted` | binding | Export, metrics |

## Rules

1. No PDF bytes or prompts in payloads.  
2. Consumers idempotent (at-least-once).  
3. New event types = minor contract bump + IDD-0006 update; renames = ADR.
