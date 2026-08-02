# Enterprise Roadmap

**Document:** `09-ENTERPRISE-ROADMAP.md`  
**Date:** 2026-08-02  
**Pillar:** Trust for labs, universities, and regulated buyers  
**Timing:** Parallel design anytime; **implementation after** personal OS P0–P1 prove value. Phases below are enterprise milestones — not the same as eng P0–P4.

**Related:** [05-RESEARCH-OS-VISION.md](05-RESEARCH-OS-VISION.md) · [04-RESEARCH-OS-ROADMAP.md](04-RESEARCH-OS-ROADMAP.md) · `docs/SECURITY_BASELINE_v1.0.md` · `docs/public-saas-readiness-pk.md`

---

## 1. Why a separate Enterprise Roadmap

The Step 0 audit covered **engineering completeness** of the personal Research OS. Enterprise buyers ask different questions:

> Can we audit access? Manage identities? Scope data by org? Prove controls?

Dhund should wrap the personal OS with enterprise controls — **not rewrite** Evidence/Writing for multi-tenancy without ADRs.

---

## 2. Current enterprise posture (honest)

| Capability | Today |
|------------|-------|
| Auth | Google, magic link, password, JWT `session_version` |
| AuthZ | Ownership + `is_admin` boolean |
| Audit | Security events + workflow events (partial) |
| API keys (customer) | Absent |
| OAuth (Dhund as IdP / app platform) | Absent (Zotero/Mendeley as clients only) |
| Orgs / teams / RBAC | Absent |
| SAML / SCIM | Absent |
| Admin portal | APIs only — no SPA |
| SOC2 / ISO / residency | Not started |
| Billing entitlements | Design only |

**Label:** Closed-beta personal OS with strong security *baseline*, weak enterprise *product*.

---

## 3. Phase E1 — Foundations (security productization)

**Outcome:** Auditable personal/team-ready tenancy without full orgs yet.

| Milestone | Detail | Effort |
|-----------|--------|--------|
| **Audit logs** | Immutable admin-readable log: auth, export, delete, sync, agent runs, evidence accept | L |
| **API keys** | User/project scoped keys for first-party automation; hashed at rest; rotate/revoke | L |
| **OAuth (app)** | Optional: Dhund OAuth apps for trusted clients (later MCP/Zapier) | L |
| **Session management** | Device/session list UI; revoke; step-up for delete/export | M |
| **Security center in Settings** | Sessions, keys, recent security events | M |

**Depends on:** Security baseline (done); Admin SPA helps but API-first OK.

**Exit:** Customer can answer “who accessed what, when?” for their account.

---

## 4. Phase E2 — Organizations & RBAC

**Outcome:** Lab can share a project library without sharing one login.

| Milestone | Detail | Effort |
|-----------|--------|--------|
| **Organizations** | Org entity, membership, billing owner | XL |
| **Teams** | Groups within org | L |
| **RBAC** | Roles: owner, admin, member, viewer; resource ACLs on projects/library | XL |
| **Shared projects / libraries** | AuthZ rewrite from pure `user_id` | XL |
| **Invite flows** | Org invites (reuse beta invite patterns) | M |

**ADRs required** before schema. Do not bolt FK across private Bases incorrectly.

**Exit:** Two researchers collaborate on one project with distinct roles.

---

## 5. Phase E3 — Identity enterprise & Admin Portal

**Outcome:** IT can provision Dhund like other SaaS research tools.

| Milestone | Detail | Effort |
|-----------|--------|--------|
| **SAML / SSO** | University / hospital IdP | XL |
| **SCIM** | User lifecycle provision/deprovision | L |
| **Admin Portal** | Full SPA: users, orgs, kill switch, budgets, audit export, payment confirm | L–XL |
| **Domain capture** | Restrict signup to verified domains | M |
| **Data export / legal hold (light)** | Org-wide export job | L |

**Exit:** IdP login + admin can offboard a user and revoke access same day.

---

## 6. Phase E4 — Compliance & residency

**Outcome:** Procurement and security questionnaires become winnable.

| Milestone | Detail | Effort |
|-----------|--------|--------|
| **SOC 2 Type I → II** | Controls, vendors, evidence collection | XL (org process) |
| **ISO 27001** | Optional track after SOC2 | XL |
| **Data residency** | Region-pinned DB/storage (Render/Neon/R2 regions) | XL |
| **DPA / subprocessors** | Public list + signed DPA | M |
| **Encryption upgrades** | Token crypto beyond itsdangerous seal if required | L |
| **Penetration test** | Annual | M |
| **HIPAA / BAA** | Only if product commits to PHI — separate decision | XL |

**Exit:** Security questionnaire packet + residency option for enterprise SKU.

---

## 7. Mapping to engineering P0–P4

| Enterprise | Engineering interaction |
|------------|-------------------------|
| E1 Audit / sessions / keys | Fits **P3 Hardening** (can start API keys after Alpha) |
| E2 Orgs / RBAC | **P4** teams — do not start before product demand |
| E3 SAML / SCIM / Admin | After E2 |
| E4 SOC2 / residency | Parallel compliance program once revenue justifies |

Personal Research OS value (Evidence → Writing) must stay ahead of enterprise chrome — or Dhund becomes a compliance shell with a weak research core.

---

## 8. Enterprise non-goals (early)

- Selling “SOC2 ready” before E1 audit logs exist  
- Building SAML before orgs  
- Multi-region before single-region reliability  
- HIPAA marketing without BAA program  

---

## 9. Success metrics

| Metric | Meaning |
|--------|---------|
| Time to answer security questionnaire | Days → hours with packet |
| Org adoption | Seats per org |
| Offboard time | <1 day access revoke |
| Audit export used in real incidents | Proven utility |

---

## 10. Sequencing summary

```text
E1  Audit logs · API keys · OAuth apps · Session management
E2  RBAC · Organizations · Teams
E3  SAML · SCIM · Admin Portal
E4  SOC2 · ISO27001 · Data residency
```
