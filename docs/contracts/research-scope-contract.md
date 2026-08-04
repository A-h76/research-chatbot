# Research Scope Policy — platform contract

**Service:** Prompt Gateway / Research Scope  
**Version:** 1.0  
**Status:** Frozen complete (ADR-0017)  
**Package:** `backend.ai.research_scope`

## Doctrine

> **Dhund optimizes every interaction for advancing research.**

Every interaction should either:

* advance research,
* support the research workflow, or
* gently redirect the user back to research.

Dhund is a **workspace with a purpose**, not a chatbot with restrictions.

```text
User
  → Prompt Gateway (scope)
  → ALLOW | CLARIFY | REDIRECT
  → (ALLOW) Capability Router → Model
```

## Primary API

```python
from backend.ai.research_scope import evaluate_research_scope, system_scope_decision

decision = evaluate_research_scope(
    user_message,
    project_name="Osteoarthritis",
    paper_scoped=False,
    research_skill="ask",
)

if decision.verdict == "redirect":
    # stream decision.user_message; do not call the LLM
    ...
elif decision.verdict == "clarify":
    ...
# else ALLOW → Capability Router / model path

# Non-chat platform paths — never classify as research prompts:
# system_scope_decision("upload")  # auth, OAuth, billing, jobs, settings
```

## Verdicts

| Verdict | Public? | Meaning | LLM? |
|---------|---------|---------|------|
| `allow` | yes | Advances research or supports workflow | Yes |
| `clarify` | yes | Ambiguous — ask for research context | No |
| `redirect` | yes | Better suited to General AI; pivot to workflow | No |
| `system` | **no** | Auth / upload / OAuth / billing / jobs | N/A (skip gate) |

## Relevance score (workflow relevance)

`ScopeDecision.relevance_score` ∈ 0–100 — “does this move research forward?”

| Score | Intended outcome |
|------:|------------------|
| > 70 | allow |
| 40–70 | clarify |
| < 40 | redirect |

## In-scope examples (ALLOW)

- Literature / paper / evidence / writing / reviewer / methodology
- Translate abstract, improve grammar, manuscript polish
- ANOVA / Kaplan–Meier / Bayesian / mixed-effects explanation
- Research coding: pandas, RNA-seq, experiment CSV, Jupyter, reproducibility

## Out-of-scope examples (REDIRECT)

- Toy coding (“add two numbers”), LeetCode, Discord bots
- Jokes, birthday poems, vacation / lifestyle asks

## Enforcement

| Mode | Env | Behavior |
|------|-----|----------|
| Soft redirect (default) | `RESEARCH_SCOPE_ENFORCEMENT=soft_redirect` | Redirect/clarify without LLM |
| Off | `RESEARCH_SCOPE_ENFORCEMENT=off` | Gateway no-op (emergency) |

Legacy: `soft_decline` ≡ soft_redirect.

## Provenance

```json
{
  "scope_gate": {
    "verdict": "redirect",
    "reason_codes": ["clear_offscope"],
    "relevance_score": 12,
    "router_version": "1.0"
  }
}
```

## Forbidden

- Framing redirects as punitive “declined” / “access denied”
- Calling the LLM for clear redirect/clarify while enforcement is on
- Rejecting research-workflow support (translation, grammar, stats, research coding)
- Running SYSTEM platform paths through the research prompt classifier
