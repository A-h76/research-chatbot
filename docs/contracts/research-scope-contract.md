# Research Scope Policy — platform contract

**Service:** Prompt Gateway / Research Scope  
**Version:** 0.1  
**Status:** Accepted (ADR-0017) — soft_decline first ship  
**Package:** `backend.ai.research_scope`

## Doctrine

Dhund is a **research operating system**, not a general AI assistant.

```text
User
  → Prompt Gateway (scope)
  → ALLOW | CLARIFY | DECLINE
  → (ALLOW) Capability Router → Model
```

## Primary API

```python
from backend.ai.research_scope import evaluate_research_scope

decision = evaluate_research_scope(
    user_message,
    project_name="Osteoarthritis",   # optional
    paper_scoped=False,
    research_skill="ask",
)

if decision.verdict == "decline":
    # stream decision.user_message; do not call the LLM
    ...
elif decision.verdict == "clarify":
    # stream clarification; do not call the LLM
    ...
# else ALLOW → existing chat / Capability Router path
```

## Verdicts

| Verdict | Meaning | LLM called? |
|---------|---------|-------------|
| `allow` | In research lifecycle (incl. scientific programming) | Yes |
| `clarify` | Ambiguous coding / vague ask — ask if research-related | No (first ship) |
| `decline` | Clear off-scope | No |

## In-scope examples (ALLOW)

- Literature / paper / evidence / writing / reviewer / methodology
- “Explain ANOVA”, “draft LaTeX”, “BibTeX”
- “pandas to analyze this experiment CSV”, “plot ROC”, “RNA-seq pipeline”
- Jupyter / reproducibility / statistical scripts

## Out-of-scope examples (DECLINE)

- “Write Python to add two numbers”
- LeetCode / interview prep / Discord bot / Minecraft / shopping / jokes

## Enforcement

| Mode | Env | Behavior |
|------|-----|----------|
| Soft decline (default) | `RESEARCH_SCOPE_ENFORCEMENT=soft_decline` | Decline/clarify without LLM |
| Off | `RESEARCH_SCOPE_ENFORCEMENT=off` | Gateway no-op (emergency) |

## Provenance on gated replies

Assistant message `sources` / metadata may include:

```json
{
  "scope_gate": {
    "verdict": "decline",
    "reason_codes": ["generic_coding"],
    "router_version": "0.1"
  }
}
```

## Relation to other layers

| Layer | Role |
|-------|------|
| Research Scope (this) | Allowed to run at all? |
| AI Capability Router | Which capability / model? |
| UFTR / Evidence / Writing | Research content + grounding |

## Versioning

- Additive reason codes / skills: minor.
- Changing default enforcement or removing ALLOW for research code: ADR + bump.
