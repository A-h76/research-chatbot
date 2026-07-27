# ✦ Soro (Personal AI / ResearchOS)

Private research & thesis writing assistant — ChatGPT-style chat grounded in
your uploads, plus a Paper Workspace, Discover, and citation tools.

Your OpenAI API key stays on the backend — never exposed to the browser.

Premium SPA frontend built with **React + TypeScript + Tailwind + shadcn/ui +
Framer Motion** (in `frontend/`), served by the Flask backend.

**Branding:** The SPA primarily brands as **Soro**. Some login/legal copy still
says Personal AI; CI/docs may say ResearchOS — same app.

**Features:** Google / magic-link login · streaming chat (Responses API) ·
Projects with instructions · selective long-term memory · PDF/Word/image
uploads · RAG over your library · Phase 1 structured paper analysis + LLM
overview · Paper Workspace (Structure / Classification / Entities / Evidence /
Graph / Related) · **Discover** (OpenAlex) with Add to Library · **Crossref**
metadata enrichment on upload · citation manager + BibTeX · writing /
compare / gaps tools · ⌘K command palette · light/dark theme.

**Using the product:** Library → upload papers (or Search → Discover → Add to
Library for metadata stubs). Open a paper for the workspace tabs. Ask Soro
from the sidebar More menu or ⌘K. Citations live under the Citations page /
toolbar.

For a full engineering inventory, see [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

---

## Quick start

```bash
pip install -r requirements.txt

# build the frontend (needs Node 18+)
cd frontend
npm install
npm run build
cd ..

# fill in .env (see below)
python server.py
# → open http://localhost:5000
```

For the research pipeline (Crossref enrich → Phase 1 → paper analysis) you also
need a **Postgres** `DATABASE_URL` and a worker process:

```bash
python run_migrations.py   # after server has created core tables once
python worker.py
```

### Developing the frontend (hot reload)

```bash
# terminal 1 — backend
python server.py            # http://localhost:5000

# terminal 2 — worker (Postgres required)
python worker.py

# terminal 3 — frontend
cd frontend && npm run dev  # http://localhost:5173 (proxies /api /auth /login)
```

---

## Setting up `.env` (one time)

Copy `.env.example` and fill in at least:

### 1. OpenAI API key (required)
`OPENAI_API_KEY=`

### 2. Postgres (required for worker / production)
Neon or any Postgres URL in `DATABASE_URL=`.

> Leave empty for SQLite API-only local play — the worker needs Postgres
> (`FOR UPDATE SKIP LOCKED`).

### 3. Google login (optional)
OAuth client + redirect `http://localhost:5000/auth/callback`. See Google Cloud
Console docs. Magic link works without Google if Resend (or console fallback)
is configured.

### 4. Who can log in
- `ALLOWED_EMAILS=` empty → any Google account may sign in
- Lock it down for public deploys: `ALLOWED_EMAILS=you@example.com`

### 5. Secrets
`FLASK_SECRET_KEY=` — long random string.

### 6. Scholarly providers (optional but recommended)

| Variable | Purpose |
|----------|---------|
| `CROSSREF_MAILTO` | Polite pool identity for Crossref (recommended) |
| `CROSSREF_PLUS_TOKEN` | Crossref Plus (optional) |
| `OPENALEX_BASE_URL` | Defaults to public OpenAlex API (no key) |
| `SEMANTIC_SCHOLAR_API_KEY` | Enables Related Papers; without it Related stays empty |
| `ENABLE_CROSSREF` / `ENABLE_OPENALEX` / `ENABLE_SEMANTIC_SCHOLAR` | Ops kill-switches (default on) |

Crossref enrichment runs in the **worker** after text extract and **before**
Phase 1. Failures are soft — uploads still succeed.

### 7. Paper Chat Stage 1 (optional)
`PAPER_CHAT_PIPELINE_ENABLED=false` (default) | `shadow` | `true`

---

## Product surfaces (short)

| Surface | What it does |
|---------|----------------|
| **Library** | Uploads, tags, processing status; metadata-only badge for Discover stubs |
| **Search** | My Library corpus search + **Discover** (OpenAlex) |
| **Paper Workspace** | Pipeline tabs + Related (Semantic Scholar) + paper chat |
| **Citations** | Manual/BibTeX; API also formats via Crossref CSL |
| **Projects / Writing / Compare** | Scoped workspaces and multi-paper tools |

Ops: `GET /api/worker/health`, `GET /api/health/providers`.

---

## File uploads, vision & RAG

- Upload from **Library** (preferred) or chat ＋
- Worker: extract → embed → Crossref (DOI) → Phase 1.1–1.7 → LLM overview
- Discover **Add to Library** stores metadata only (no third-party PDF fetch);
  upload a PDF later for analysis/RAG
- Images can go to vision-capable models in chat

---

## Deploy

**Docker / Railway:** multi-stage `Dockerfile` + `entrypoint.sh` (Gunicorn on
`0.0.0.0:$PORT`). Run a separate worker service with the same image /
`python worker.py`. Apply migrations (`run_migrations.py`) against Postgres.

**Classic:** build frontend, set env vars, add Google redirect URI, then:

```bash
gunicorn -w 2 -k gthread --threads 8 -b 0.0.0.0:$PORT server:app
```

systemd units live under `deploy/systemd/`.

---

## Tests & lint

```bash
pytest
flake8 .
cd frontend && npm test && npm run lint
```

CI (`.github/workflows/ci.yml`) runs flake8 + pytest against Postgres + Redis.

---

## Notes

- Not official ChatGPT — private research workspace.
- Architecture constraints and ADRs: `docs/00-constitution.md`,
  `PROJECT_STATUS.md`.
- “Training”: model weights aren’t fine-tuned via API; memory + library + Phase 1
  provide durable context instead.
