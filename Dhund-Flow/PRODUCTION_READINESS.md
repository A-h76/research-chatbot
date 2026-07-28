# PRODUCTION_READINESS — Deploy & ops

**Last updated:** 2026-07-28  
**Overall readiness (closed beta):** ~**7 / 10**  
**Not:** open public multi-tenant SaaS-hardened

---

## Scores (indicative)

| Area | /10 | Note |
|------|-----|------|
| Architecture | 7 | Unified analysis path; dual stacks remain |
| Security | 6–7 | PR1–4 mitigations; still verify live host |
| Performance | 5 | Personal scale; linear RAG |
| Scalability | 4 | Single-node friendly |
| Maintainability | 5 | `server.py` monolith |
| UX | 8 | Research OS chrome |
| Deployment | 5–6 | systemd / Procfile / Dockerfile; migrations through 0033 |
| Observability | 6 | Prometheus + JSON logs; no Sentry |
| Testing | 7 | Large pytest; frontend Vitest not in CI |

---

## Deploy checklist (minimum)

1. Postgres (worker requires it — SQLite is API-only)  
2. Run migrations through **0033** (Writing + Evidence)  
3. `FLASK_SECRET_KEY` set (no random multi-process fallback in prod)  
4. `DEV_AUTO_LOGIN` off — startup should refuse if left on in prod  
5. `ALLOWED_EMAILS` / invite gates for closed beta  
6. Object storage (R2/S3/local) configured  
7. Optional Redis for multi-worker rate limit  
8. Worker process + web process  
9. Confirm `/metrics` token or loopback-only  
10. Smoke: login → library upload → Evidence extract → Writing Studio  

Scripts / notes: `deploy/`, `scripts/`, `docs/testing-guide.md`

---

## Security ops (summary)

| Control | State |
|---------|-------|
| OAuth / magic link / session TTL | Implemented |
| Ownership checks (typical 404) | Implemented |
| Chat rate limit + analysis token quota | Mitigated (PR1) |
| Metrics auth / worker bind | Mitigated (PR2) |
| Magic-byte MIME + optional ClamAV | Mitigated (PR3) |
| Security headers / CSP Report-Only | Mitigated (PR4) |
| Dependency audit in CI | Missing |
| Sentry / paging | Missing |
| Payments | Not built |

---

## Current risks

### Security
- Open signup + blank allowlist on public deploy → cost abuse  
- Spoofed uploads if magic validation bypassed in a path  
- Prompt injection via uploaded document text  

### Scaling
- O(n) RAG cosine  
- In-memory limiter if Redis unset  
- Full-document memory on import  

### AI
- Hallucinated citations if features bypass Evidence Query  
- Dual chat vs Prompt Engine paths confuse ownership  

### Infrastructure
- Worker misconfigured against SQLite “works for API”  
- No Sentry → silent failures  
- Schema dual-bootstrap drift (create_all vs migrations)  

### Business
- No payments/tenancy packaging  
- Branding inconsistency  

---

## Missing / incomplete (checklist)

- [ ] Frontend build + Vitest in CI  
- [ ] Deploy pipeline / Dependabot / pip-audit  
- [ ] Sentry + product analytics  
- [ ] Documented backup runbooks  
- [ ] Step-up reauth for account deletion  
- [ ] Billing (SaaS-PK track)  
- [ ] Horizontal scaling story beyond SKIP LOCKED workers  

---

## Related

- [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)  
- [FEATURE_MATRIX.md](FEATURE_MATRIX.md)  
- `docs/public-saas-readiness-pk.md`
