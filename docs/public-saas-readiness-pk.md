# Public SaaS readiness (9/10) — Pakistan / ~100 users

**Goal:** Move from closed-beta **7/10** → public-capable **9/10** without Stripe/PayPal.  
**Constraint:** Founder in Pakistan; initial target **~100 users**; local wallets (JazzCash, EasyPaisa, NayaPay, SadaPay).  
**Not in this gate:** Writing Studio 2.1–2.5 (product differentiation after Phase 2.0 validation).

**Companions:** [`PROJECT_STATUS.md`](../PROJECT_STATUS.md) §16–17 · [`phase-2.0-ops-readiness.md`](./phase-2.0-ops-readiness.md)

---

## Pricing matrix (as designed) → engineering entitlements

Map marketing rows to **enforceable caps** in code. Anything you cannot meter yet must not be sold as unlimited.

| Plan | Price | Projects | Papers | AI runs / mo | Compare size | Notes |
|------|-------|----------|--------|--------------|--------------|-------|
| Free | 0 | 2 | 25 | 15 | 2 papers | Acquisition; tight AI |
| Founding Student | PKR 349 | ∞* | 500 | 100 | 20 | Early supporters; lock price forever for these accounts |
| Student | PKR 699 | ∞* | 2,000 | 300 | 50 | Core paid |
| Pro | TBD | ∞* | 10,000+ | High + fair-use | Large | Power users |
| Team / University | TBD | Shared | Shared library | Shared quota | Collab | Defer until >100 users |

\* “Unlimited projects” still needs a soft ceiling (e.g. 100) to stop abuse.

### Product honesty check (important)

| Matrix feature | Today | Sell as |
|----------------|-------|---------|
| AI Chat | Live | OK |
| Cross-paper / Compare | Live (limits by plan) | OK if capped |
| Research Memory | Live (basic vs full = feature flags) | OK |
| Citation manager | Live | OK |
| BibTeX/RIS import | Live for all authenticated | **Don’t gate Free off import** — Library is the product; Free without import feels broken. Cap *papers stored* instead. |
| Zotero sync | Live (Phase 1b) | Matrix says “future” but product has it — either ship as paid or mark Free-limited (e.g. sync once/week). |
| Literature review generation | **Not built** (Phase 2.4) | Mark **Coming soon** or remove from paid checkmarks until live |
| Evidence insertion | **Not built** (Phase 2.2) | Same |
| Export DOCX/PDF/LaTeX | Partial (Markdown/BibTeX stronger) | Don’t promise LaTeX/DOCX until exporters exist |
| Collaboration / shared library | **Not built** | Team tier = waitlist only for now |

**Rule:** Paid plans may advertise roadmap features only with explicit “beta / coming” — never as delivered checkmarks.

---

## Billing without Stripe (recommended for ~100 users)

Do **not** integrate four PSPs on day one. That is weeks of merchant KYC, webhooks, and reconciliation for tiny volume.

### Phase B0 — Manual local pay (ship with open signup) ✅ recommended first

```text
User picks plan → sees payment instructions (JazzCash / EasyPaisa / bank)
     → pays with reference = dhund-<user_id>-<order_id>
     → submits “I’ve paid” (screenshot optional) + txn id
     → Admin (you) confirms in admin UI → plan activates + invoice row
```

| Piece | Build |
|-------|--------|
| `plans` + `subscriptions` + `payment_orders` tables | Plan code, status, period end, PKR amount |
| Entitlements on `users` or join table | `plan_code`, paper limit, AI run limit, compare limit |
| Checkout UI | Instructions + copyable reference + upload proof |
| Admin | List pending payments → Confirm / Reject |
| Invoices | Simple PDF or HTML receipt (manual is fine) |

**Wallets at this stage:** JazzCash + EasyPaisa numbers (or merchant QR) published in UI. NayaPay/SadaPay as “transfer to …” if you have personal/business accounts — same manual confirm flow.

**Why this is correct at 100 users:** Hours to operate, days to build, zero PSP dependency, works in Pakistan tomorrow.

### Phase B1 — Semi-auto (when confirmations hurt)

- One primary: **JazzCash Merchant** or **EasyPaisa Merchant** (whichever KYC you clear first)
- Webhook / return URL → mark `payment_orders` paid → activate subscription
- Keep EasyPaisa/NayaPay/SadaPay as **manual fallback** channels

### Phase B2 — Multi-PSP (only if volume demands)

Second wallet API + reconciliation jobs. Skip until you have real load.

### Explicitly out of scope for 9/10

- Stripe Atlas / PayPal (unavailable / painful from PK)
- Crypto-only billing as primary

---

## 9/10 checklist (adapted)

### Must have

| # | Item | Pakistan / 100-user note |
|---|------|---------------------------|
| 1 | Open registration + abuse controls | Email verify (magic link already); rate-limit signup/OAuth; optional waitlist flag; invite-only becomes `false` when B0 billing live |
| 2 | Tenant isolation audit | Automated tests: cross-user file/project/citation/library access → 404/403 |
| 3 | Unified upload + storage policy | One allowlist/MIME/size; R2 (or S3) only in prod — no local disk |
| 4 | Horizontal story | Document: N× `worker.py` + Redis limiter + Postgres + R2 |
| 5 | Deploy pipeline | Staging → prod; migrations in deploy; rollback note; health checks |
| 6 | Support ops | `/support` triage daily; public “known issues” doc or Notion page |
| 7 | Light analytics | Funnel events: signup → first import → first Research Ready (PostHog self-host or simple `product_events` table) |
| 8 | Real feature flags | Kill: Discover, attach auto-analysis, expensive chat models, Compare |
| 9 | **Billing + plans (local)** | B0 manual JazzCash/EasyPaisa + entitlements enforcing the matrix |

### Strongly recommended

| Item | Note |
|------|------|
| pgvector / indexed RAG | When paper counts approach Student/Pro caps |
| Paper-chat → PromptBuilder | One AI stack |
| Admin UI | Confirm payments, disable users, flip flags, adjust plan |

### Not required for platform 9/10

Writing Studio 2.1–2.5 — ship after Phase 2.0 validation; then attach to Student+ entitlements.

---

## Enforcement map (what code must check)

Reuse / extend `quotas/`:

| Cap | Enforce on |
|-----|------------|
| Projects | `POST /api/projects` |
| Papers stored | upload, import, Discover import, sync create, attach |
| Monthly AI research runs | `phase1_analysis` / `paper_analysis` / chat research actions — define one counter |
| Compare paper count | Compare/gaps request body |
| Import formats | Prefer: Free gets BibTeX/RIS; paid gets Zotero/Mendeley sync frequency or paper ceiling |
| Export formats | Gate DOCX/PDF/LaTeX when those exporters exist |

Soft vs hard caps:

- Soft: warn at 80%  
- Hard: 403 with upgrade CTA  
- Fair-use on Pro “High/Unlimited”: daily token budget + kill switch flag  

---

## Suggested build order (to 9/10)

```text
1. Plans + entitlements schema + QuotaService plan limits
2. Admin: set plan manually (you can sell Founding before checkout UI)
3. Checkout UI + payment_orders + proof (JazzCash/EasyPaisa instructions)
4. Open signup (invite-only off) + rate limits + email verify
5. Tenant isolation test suite
6. Unify upload policy + R2-only prod docs
7. Feature flags service (read migration 0008 or thin env+DB hybrid)
8. Deploy pipeline + health checks documented
9. Light funnel events
10. Support known-issues page
→ Declare 9/10 public SaaS (PK)
Then: Phase 2.0 sessions if not done / Writing Studio / JazzCash merchant API
```

**Parallel:** Keep running Phase 2.0 researcher sessions — billing readiness ≠ product validation.

---

## Founding Student operations tip

At PKR 349, AI cost can exceed revenue quickly.

- Cap **100 AI runs** hard; count phase1 + paper_analysis + heavy chat  
- Founding cohort: max N seats (e.g. first 50) then close the plan  
- Prefer annual prepay later; monthly is fine at 100 users with manual renew  

---

## Definition of done (9/10)

- [ ] Stranger can register, verify email, land on Free  
- [ ] Can pay Student/Founding via JazzCash or EasyPaisa and get plan within 24h (manual OK)  
- [ ] Paper / project / AI caps enforced server-side  
- [ ] Cross-tenant access tests green  
- [ ] Prod uses object storage + Redis limiter + ≥1 worker; deploy runbook exists  
- [ ] Sentry or equivalent errors visible  
- [ ] Flags can disable Discover / analysis without redeploy  
- [ ] Legal pages non-placeholder; support path works  
- [ ] Matrix features that aren’t built are labeled Coming soon  

---

*Local wallets + entitlements beat unfinished Stripe. Automate JazzCash when confirmation load > ~10 payments/week.*
