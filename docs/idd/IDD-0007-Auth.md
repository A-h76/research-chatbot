# IDD-0007 — Authentication, Authorization & Errors

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Owners** | Developer A (implementation), Developer B (route guards / UX) |

---

## 1. Authentication

### 1.1 Mechanisms

| Mechanism | How | Client |
|-----------|-----|--------|
| Session cookie | Google OAuth, magic link, password ops, dev login | SPA default |
| Bearer JWT | `GET /api/auth/jwt` then `Authorization: Bearer` | Upload, bulk, pipeline, RAG |
| Marketing | Unauthenticated | Jinja pages only |

### 1.2 Session rules

- `user_id` in server session; SPA boot via `GET /api/me`.
- Logout clears session; JWT `session_version` mismatch → `401`.
- Closed beta: invite allowlist; denied signup → `403` with clear detail.

### 1.3 Protected application routes (Frontend)

All SPA routes under `RootLayout` require successful `/api/me` except legal/support if exposed without shell.

Hard redirect to `/login` on auth failure.

---

## 2. Roles

| Role | Description |
|------|-------------|
| `anonymous` | Marketing only |
| `user` | Standard researcher |
| `beta_user` | Invited closed beta (same permissions as user unless gated) |
| `admin` | Ops (`is_admin`) — invites, metrics, kill switches |

No multi-user project roles in v1 (single owner).

---

## 3. Permissions matrix

| Action | Rule |
|--------|------|
| Read/write Project | `project.user_id == me.id` |
| Read/write Paper | `paper.user_id == me.id` |
| List/extract Evidence | `evidence.project_id` owned by me |
| Accept/reject Evidence | same + project ownership |
| Writing document | `document.user_id == me.id` |
| Bind citation | document + evidence both owned; same project |
| Admin ops | `is_admin` |

Cross-tenant access → **403** (not 404) when existence is confirmed; **404** allowed to avoid leaking IDs if preferred—**pick one policy and keep consistent**. Recommended: **404 for missing or not-owned** on GET by id.

---

## 4. Authorization on EvidenceQuery

Server **ignores** client-supplied `user_id` inside query scope; injects authenticated user.  
`scope.project_id` must be owned or request fails.

---

## 5. Error model

### 5.1 Standard body

```json
{
  "error": "validation_error",
  "detail": "scope.project_id is required",
  "fields": {
    "scope.project_id": ["required"]
  }
}
```

### 5.2 Stable `error` codes

| Code | HTTP | Meaning |
|------|------|---------|
| `not_authenticated` | 401 | Login required |
| `forbidden` | 403 | Authenticated but not allowed |
| `not_found` | 404 | Missing resource |
| `validation_error` | 400 | Bad input / EvidenceQuery contract break |
| `insufficient_evidence` | 200\* or 400 | Writing blocked—prefer **200 with status=blocked** in grounded writing |
| `not_research_ready` | 400 | Extract gated |
| `conflict` | 409 | Autosave / duplicate job |
| `rate_limited` | 429 | Too many requests |
| `internal_error` | 500 | Unexpected |
| `dependency_unavailable` | 503 | OpenAlex, OAuth provider, etc. |

\*Product preference: grounded writing returns `200` + `status: "blocked"` so UI can render CTA without treating as transport failure.

### 5.3 Validation

- Fail closed on forbidden EvidenceQuery keys.
- Enum values must match IDD-0002 constants.
- File size / MIME validated server-side on upload.

### 5.4 Rate limit

Return `429` with `Retry-After` when available. Frontend: toast + disable CTA briefly.

---

## 6. Security requirements (contract-level)

1. No LLM provider keys in Frontend.
2. Presigned URLs expire; do not log secrets.
3. Support/early-access endpoints remain rate-limited.
4. Admin routes under `/api/admin/**` require admin role.
