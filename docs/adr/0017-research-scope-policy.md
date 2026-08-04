# ADR-0017: Research Scope Policy — Prompt Gateway

Status: accepted  
Date: 2026-08-04

## Context

Dhund is a **Research Operating System**, not a general-purpose ChatGPT clone.
Allowing every prompt (e.g. “write Python to add two numbers”) trains users to
treat Dhund as a generic assistant and dilutes product identity.

The question is not “Can the model write code?” — it can. The question is
**Should Dhund allow this request in this workspace?**

This mirrors UFTR and the AI Capability Router: resolve behind a platform
boundary; keep the system inspectable; strengthen the research lifecycle.

## Decision

### Product doctrine

> **Dhund is not a general AI assistant that can do research.**  
> **Dhund is a research operating system that uses AI to accelerate every stage
> of the research lifecycle.**

### Prompt Gateway (binding)

```text
User prompt
      ↓
Prompt Gateway (Research Scope)
      ↓
ALLOW | CLARIFY | DECLINE
      ↓ (ALLOW)
Capability Router → Provider → Model
```

**First-ship enforcement: soft decline / clarify** — polite identity-preserving
response **without** calling the LLM for clear off-scope asks. Not a hard HTTP
error. Env: `RESEARCH_SCOPE_ENFORCEMENT=soft_decline|off` (default `soft_decline`).

### What belongs (ALLOW)

Requests that contribute to the research lifecycle, including:

- Literature discovery, paper understanding, evidence synthesis
- Academic writing, citation, peer review, publication prep
- Methodology, statistics, experimental design
- **Research programming**: pandas/NumPy/R/MATLAB/SPSS, bioinformatics,
  Jupyter, visualization, ML experiments, reproducibility / sequencing pipelines
- LaTeX, ANOVA explanation, experiment CSV analysis

### What does not (DECLINE)

- Generic coding homework / LeetCode / interview prep
- Consumer apps (Discord bots, Minecraft plugins, websites-for-fun)
- Entertainment, shopping, unrelated casual chat
- Anything that does not advance research work

### Ambiguous coding (CLARIFY)

Short “write Python…” with no research cues — especially when a project is open —
gets a **workspace-aware clarification** (is this for your research analysis /
plots / reproducibility?) instead of generating homework code.

### Layers (platform stack)

1. Intent / scope classification (this ADR)  
2. Policy engine (workspace / mode permissions — evolve)  
3. Tool permissions (web, code exec — evolve)  
4. Project isolation (existing authz)  
5. Grounding (Evidence / Writing — existing)

Capability Router (ADR-0016) runs **after** ALLOW.

### Non-goals

- Absolute ban on all programming
- Replacing researcher judgment
- Turning every chat into Evidence Chat permissions on day one

## Alternatives considered

| Option | Why not |
|--------|---------|
| Soft nudge but still answer off-scope | Weak identity; still feels like ChatGPT |
| Hard block (4xx) | Hostile UX; identity message never lands |
| LLM-only “be researchy” system prompt | Unreliable; still burns tokens on homework |

## Consequences

- Chat `/api/chat` runs Research Scope before model calls.
- Decline/clarify replies are saved as assistant messages with provenance
  `scope_gate`.
- Identity doctrine markdown updated to match.
- Living contract: [`docs/contracts/research-scope-contract.md`](../contracts/research-scope-contract.md).

## Cost / Security / Observability / Extensibility

- **Cost:** Off-scope prompts no longer hit frontier models.  
- **Security:** First policy layer of the Prompt Gateway.  
- **Observability:** Decision logged on the reply (verdict + reason codes).  
- **Extensibility:** Swap heuristic classifier for a small model later via DI.
