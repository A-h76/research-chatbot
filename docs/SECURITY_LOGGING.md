# Security logging policy (closed beta)

## Never log
- Passwords, password hashes, reset/verification tokens
- API keys, `Authorization` headers, session cookies
- Full research prompts, PDF/document bodies, chat message content
- Raw uploaded file bytes

## Always log (structured `security` logger + durable `security_events` for critical subset)
- Auth denials (OAuth / magic / invite)
- Rate-limit exceeded
- CSRF blocked
- Authz denied (ownership)
- Quota / daily budget / AI kill-switch blocks
- Virus detections
- Admin kill-switch / budget / plan changes
- Session revoked-all / password changed / email verified

## Diagnostics
Opt-in only (`DIAGNOSTICS_OPT_IN=1` or future per-user flag). Do not dump research content into application logs by default.

## Related
- `security/ops/events.py` — `PERSIST_EVENTS` whitelist for DB rows
- `log_security_event()` in `server.py` — always-on structured log line
