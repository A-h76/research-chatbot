# Assistant Engine + Research State — contract v0

**Service:** Assistant Engine (decision brain)  
**Version:** 0.1 (architecture freeze; implementation slices pending)  
**Status:** Accepted — Slices 1–5 landed. **Four cores frozen.** No new engines until FE Phase 2 + researcher testing demand them.  
**ADR:** [ADR-0018](../adr/0018-assistant-engine-research-state.md)  
**Peers:** [ADR-0016 Capability Router](../adr/0016-ai-capability-router.md) · [ADR-0012 Chat orchestration](../adr/0012-chat-orchestration.md)

## Binding principles

1. **Assistant Engine decides *what* help is needed. Capability Router decides *how* to execute.**
2. **LLMs generate language. Dhund generates decisions.**
3. **Research State is computed from system signals — never LLM-guessed stages.**
4. **Frontend looks; backend thinks.**
5. Public API is domain-oriented (`/api/assistant/...`), not `/mentor/...`.
6. **The system may know everything. The UI shows only what helps the current task.**
7. **Research State is internal.** Product UI receives a thin **view model** (status / recommendation / context), not a Research State dump. Dhund must not become Jira for research.

## Canonical flow

```text
Research State (internal)
  → Assistant Engine decision
  → UI Hint / View Model  { title, subtitle, primaryAction }
  → Render

Assistant Turn (chat)
  → Assistant Engine
  → Capability Router (only if LLM needed)
  → Prompt Builder → Gateway → LLM
```

## Per-page UI budget

| Slot | Example |
|------|---------|
| One status | Ready / Needs review / Processing / Writing |
| One recommendation | Review contradictions → |
| One context | 9 papers |

Research Intelligence may show slightly more corpus context; still no KPI wall.

## Research State (internal domain shape — v0)

Computed aggregate for engines. **Not** the default FE contract for every page.
`/api/assistant/research-state` may exist for Home mentor / debug; prefer session/turn
payloads and future surface view models (`/api/assistant/view/home`, etc.) for product UI.

```json
{
  "user": {
    "experience": "beginner",
    "goals": ["lit_review"],
    "fields": ["ai", "medicine"]
  },
  "project": {
    "id": 12,
    "title": "Artificial Intelligence in Healthcare",
    "discipline": null
  },
  "corpus": {
    "papers": 9,
    "evidence": 342,
    "themes": 12,
    "gaps": 3,
    "contradictions": 3,
    "coverage": 0.92
  },
  "workflow": {
    "stage": "evidence_extraction",
    "completion": { "done": 3, "total": 7 },
    "nextAction": {
      "id": "extract_evidence",
      "label": "Extract evidence",
      "href": "/research/compare?tab=extract"
    },
    "blockers": []
  },
  "writing": {
    "hasManuscript": false,
    "citationCount": 0,
    "reviewComplete": false
  }
}
```

### Stage derivation (illustrative — implement as pure functions)

| Signals | Stage |
|---------|--------|
| No project / 0 papers | `discovery` / `library` |
| Papers > 0, evidence == 0 | `evidence_extraction` |
| Evidence > 0, themes/gaps pending | `synthesis` |
| Writing exists, review incomplete | `writing` |
| Review complete | `review` / `publish` path |

## Assistant Turn API (target)

`POST /api/assistant/turn`

**Request (sketch):**

```json
{
  "message": "Hi",
  "project_id": 12,
  "surface": "home",
  "conversation_id": null
}
```

**Response discriminated union (sketch):**

```json
{
  "intent": "greeting",
  "mode": "companion",
  "research_state": { "...": "..." },
  "outcome": "local_reply",
  "local_reply": {
    "lines": [
      "Good evening, Ahmad.",
      "You're currently working on Artificial Intelligence in Healthcare.",
      "Before we continue — what are you trying to accomplish today?"
    ],
    "action_card": {
      "title": "What would you like to do today?",
      "actions": [
        { "id": "continue_lit_review", "label": "Continue my literature review", "href": "/research/compare" },
        { "id": "extract_evidence", "label": "Extract evidence", "href": "/research/compare?tab=extract" }
      ]
    }
  }
}
```

Other outcomes: `start_job` (stream via existing chat/job path), `ask_profile` (structured questions), `navigate` (CTA only).

## Modes

`companion` | `coach` | `teacher` | `research_partner` | `reviewer`

Selected by Assistant Engine before Prompt Builder runs.

## Implementation slices

| Slice | Deliverable | Wire freeze? |
|-------|-------------|--------------|
| 1 | Research State compute + read | Additive fields OK |
| 2 | `POST /api/assistant/turn` local outcomes | Soft |
| 3 | Intent gating (no LLM on greetings) | Soft |
| 4 | Mode-composed prompts via Prompt Builder | Soft — landed 2026-08-08 |
| 5 | All conversational surfaces on Assistant Engine | Soft freeze — landed 2026-08-08 |

### Slice 5 surfaces (shared brain)

| Surface | How it uses Assistant Engine |
|---------|------------------------------|
| Home Mentor | session + turn + action cards (FE) |
| `/api/chat` (Welcome, Conversation, project chat) | turn short-circuit + mode layers |
| Paper Chat | same short-circuit + assistant layers on paper prompt |
| Writing assist panel | Research State next-action coach strip |

## Non-goals (v0)

- Replacing Capability Router or Workflow Engine  
- LLM-as-judge for journey stage  
- Big-bang chat rewrite  
- Public `/api/mentor/*` namespace
