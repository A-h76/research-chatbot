# ADR-0017: Research Scope Policy — Prompt Gateway

Status: accepted (frozen v1.0 — complete)  
Date: 2026-08-04

## Context

Dhund is a **Research Operating System**, not a general-purpose ChatGPT clone.
The failure mode is not “answering a joke” once — it is training users to treat
Dhund as a generic assistant until the product identity dissolves.

Competitors that answer birthday poems and jokes inside a research project are
usually making a deliberate **Philosophy A** choice (general AI + research
features). Dhund chooses **Philosophy B**: **a workspace with a purpose** —
not a chatbot with restrictions.

## Decision — doctrine (binding)

> **Dhund optimizes every interaction for advancing research.**

Every interaction should either:

* **advance research**,
* **support the research workflow**, or
* **gently redirect the user back to research**.

Freeze wording:

> **Every AI interaction inside a Research Workspace must either advance the
> research directly or support the research workflow. Requests that do neither
> are redirected to a General AI workspace (if available) or answered with a
> purpose-preserving redirect — not framed as censorship.**

The gate asks **“Does this move the research forward?”** (workflow relevance),
not merely **“Is this about research?”**

| Prompt | Advances / supports workflow? | Verdict |
|--------|------------------------------|---------|
| Summarize this paper | ✅ | ALLOW |
| Translate this abstract | ✅ | ALLOW |
| Improve grammar | ✅ | ALLOW |
| Write reviewer response | ✅ | ALLOW |
| Explain Kaplan–Meier | ✅ | ALLOW |
| Generate Python for RNA-seq | ✅ | ALLOW |
| Tell me a joke | ❌ | REDIRECT |
| Plan my vacation | ❌ | REDIRECT |
| Write a birthday poem | ❌ | REDIRECT |

### Prompt Gateway (binding)

```text
User prompt
      ↓
Research Scope Gate          ← first platform boundary
      ↓
ALLOW | CLARIFY | REDIRECT   ← public outcomes
      ↓ (ALLOW)
Research Job → Capability Router → … → AI Ledger
```

| Verdict | Meaning | LLM? |
|---------|---------|------|
| **ALLOW** | Advances research or supports the workflow | Yes |
| **CLARIFY** | Ambiguous — likely research if framed | No (ask for context) |
| **REDIRECT** | Better suited to General AI; pivot back to workflow | No |

**Internal only:** `SYSTEM` — auth, uploads, connector OAuth, billing, settings,
background jobs. These paths **must not** enter the research classifier
(`system_scope_decision(...)` / skip the gate). Never user-facing.

**First-ship enforcement:** soft redirect / clarify without calling the LLM.
Env: `RESEARCH_SCOPE_ENFORCEMENT=soft_redirect|off` (default `soft_redirect`;
legacy `soft_decline` accepted as alias).

Redirect copy is **purposeful + productive** (not “Access denied”):

> This workspace is dedicated to academic research… If you're taking a break,
> I'm still here when you're ready to continue your literature review, analyze
> a paper, improve your manuscript, or verify evidence.

### Hard product rule

> **By default, every conversation inside a research project is research-scoped.**

**Future escape hatch:** a separate **General AI** workspace where anything goes.

### Relevance score (workflow relevance)

Heuristics emit optional `relevance_score` (0–100). Intended bands:

| Score | Outcome |
|------:|---------|
| > 70 | ALLOW |
| 40–70 | CLARIFY |
| < 40 | REDIRECT |

A future lightweight classifier can replace phrase lists without changing the
public ALLOW / CLARIFY / REDIRECT API.

### Same design principle as sibling primitives

| Primitive | Pattern |
|-----------|---------|
| **UFTR** | Can’t obtain PDF → explain why → offer alternatives (not “Failed.”) |
| **Research Scope** | Not research → redirect → stay purposeful (not “Access denied.”) |
| **Capability Router** | Need deep synthesis → resolve provider → execute (not “Pick Claude.”) |

> **Hide implementation complexity, expose honest outcomes, and keep the user
> moving through the research workflow.**

### Layers (platform stack)

1. Research Scope Gate (this ADR)  
2. Research Job  
3. Capability Router (ADR-0016)  
4. Prompt / Model Registry → Gateway → Validation → AI Ledger  

### Non-goals

- Absolute ban on all programming  
- Hostile “request declined” / censorship framing  
- Running auth/upload/billing through the research classifier  
- Replacing researcher judgment  

## Alternatives considered

| Option | Why not |
|--------|---------|
| Soft nudge but still answer off-scope | Weak identity; still feels like ChatGPT |
| Hard block (4xx) / “declined” | Hostile UX; feels like censorship |
| LLM-only “be researchy” system prompt | Unreliable; still burns tokens on jokes |

## Consequences

- Chat `/api/chat` runs Research Scope before model calls.
- Redirect/clarify replies are saved with `scope_gate` provenance
  (includes `relevance_score` when set).
- Identity doctrine matches this ADR.
- Living contract: [`docs/contracts/research-scope-contract.md`](../contracts/research-scope-contract.md).

## Cost / Security / Observability / Extensibility

- **Cost:** Off-topic prompts no longer hit frontier models.  
- **Security:** Reduces accidental tool use on consumer asks.  
- **Observability:** Gate provenance + relevance_score.  
- **Extensibility:** Swap heuristics for a scored classifier; keep public verdicts.
